import asyncio
import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from lib.job_queue import JobQueue
from lib.storage import Storage
from lib.workflow import Pipeline as WorkflowPipeline
from models import Record


async def _update_job_status(
    job_queue: JobQueue, storage: Storage, job_id: int, **kwargs: Any
) -> None:
    """update job in both memory and database"""
    job_queue.update_job(job_id, **kwargs)
    await storage.update_job(job_id, **kwargs)


def process_job_in_thread(
    job_id: int,
    pipeline_id: int,
    seed_file_path: str,
    job_queue: JobQueue,
    storage: Storage,
) -> None:
    """run job processing in a background thread"""
    thread = threading.Thread(
        target=_run_job_async,
        args=(job_id, pipeline_id, seed_file_path, job_queue, storage),
        daemon=True,
    )
    thread.start()


def _run_job_async(
    job_id: int,
    pipeline_id: int,
    seed_file_path: str,
    job_queue: JobQueue,
    storage: Storage,
) -> None:
    """wrapper to run async job in thread"""
    try:
        # create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            _process_job(job_id, pipeline_id, seed_file_path, job_queue, storage)
        )
    except Exception as e:
        logger.error(f"Job thread failed: {e}")
    finally:
        loop.close()


async def _process_job(
    job_id: int,
    pipeline_id: int,
    seed_file_path: str,
    job_queue: JobQueue,
    storage: Storage,
) -> None:
    """execute pipeline for seeds from file with progress tracking"""
    try:
        # load pipeline
        pipeline_data = await storage.get_pipeline(pipeline_id)
        if not pipeline_data:
            await _update_job_status(
                job_queue,
                storage,
                job_id,
                status="failed",
                error="Pipeline not found",
                completed_at=datetime.now().isoformat(),
            )
            return

        pipeline = WorkflowPipeline.load_from_dict(pipeline_data["definition"])

        # load seed file
        seed_path = Path(seed_file_path)
        if not seed_path.exists():
            raise FileNotFoundError(f"Seed file not found: {seed_file_path}")

        with open(seed_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # seeds format: [{"repetitions": 5, "metadata": {...}}, ...]
        seeds_data = data if isinstance(data, list) else [data]

        # calculate total executions
        total_executions = sum(
            (seed.get("repetitions", 1) if isinstance(seed.get("repetitions"), int) else 1)
            for seed in seeds_data
        )

        start_msg = (
            f"[Job {job_id}] Starting pipeline {pipeline_id} with "
            f"{len(seeds_data)} seeds ({total_executions} total executions)"
        )
        logger.info(start_msg)

        records_generated = 0
        records_failed = 0
        execution_index = 0

        # process each seed
        for seed in seeds_data:
            # check for cancellation
            job_status = job_queue.get_job(job_id)
            if job_status and job_status.get("status") == "cancelled":
                logger.info(
                    f"[Job {job_id}] Cancelled at execution {execution_index}/{total_executions}"
                )
                break

            # get repetitions and metadata
            repetitions = seed.get("repetitions", 1)
            if not isinstance(repetitions, int):
                repetitions = 1

            metadata = seed.get("metadata", {})

            # execute pipeline repetitions times for this seed
            for i in range(repetitions):
                execution_index += 1

                # check for cancellation
                job_status = job_queue.get_job(job_id)
                if job_status and job_status.get("status") == "cancelled":
                    cancel_msg = (
                        f"[Job {job_id}] Cancelled at "
                        f"execution {execution_index}/{total_executions}"
                    )
                    logger.info(cancel_msg)
                    break

                # update progress
                progress = execution_index / total_executions
                await _update_job_status(
                    job_queue,
                    storage,
                    job_id,
                    current_seed=execution_index,
                    progress=progress,
                    current_block=None,
                    current_step=f"Processing execution {execution_index}/{total_executions}",
                )

                try:
                    # execute pipeline with metadata as input and job tracking
                    result, trace, trace_id = await pipeline.execute(
                        metadata, job_id=job_id, job_queue=job_queue, storage=storage
                    )

                    # extract pipeline_output from final accumulated state
                    pipeline_output = ""
                    if trace and len(trace) > 0:
                        final_state = trace[-1].get("accumulated_state", {})
                        pipeline_output = final_state.get("pipeline_output", "")

                        # ensure output is a string (might be dict from metrics)
                        if isinstance(pipeline_output, dict):
                            pipeline_output = json.dumps(pipeline_output)
                        elif not isinstance(pipeline_output, str):
                            pipeline_output = str(pipeline_output)

                    # create record from pipeline output
                    record = Record(
                        output=pipeline_output,
                        metadata=metadata,
                        trace=trace,
                    )

                    # save record with job_id
                    await storage.save_record(record, pipeline_id=pipeline_id, job_id=job_id)
                    records_generated += 1

                    # update count and clear block info
                    await _update_job_status(
                        job_queue,
                        storage,
                        job_id,
                        records_generated=records_generated,
                        current_block=None,
                        current_step=f"Processing execution {execution_index}/{total_executions}",
                    )

                except Exception as e:
                    records_failed += 1
                    logger.error(f"[Job {job_id}] Execution {execution_index} failed: {e}")

                    # update failed count
                    await _update_job_status(
                        job_queue, storage, job_id, records_failed=records_failed
                    )

                    # skip and continue
                    continue

        # clean up temp file
        try:
            seed_path.unlink()
        except Exception:
            pass

        # mark as completed (or check if cancelled)
        final_status = job_queue.get_job(job_id)
        if final_status and final_status.get("status") != "cancelled":
            completed_at = datetime.now().isoformat()
            await _update_job_status(
                job_queue,
                storage,
                job_id,
                status="completed",
                progress=1.0,
                completed_at=completed_at,
            )
            logger.info(
                f"[Job {job_id}] Completed: {records_generated} generated, {records_failed} failed"
            )

    except Exception as e:
        error_msg = str(e)
        logger.error(f"[Job {job_id}] Failed: {error_msg}")

        # mark as failed
        completed_at = datetime.now().isoformat()
        await _update_job_status(
            job_queue,
            storage,
            job_id,
            status="failed",
            error=error_msg,
            completed_at=completed_at,
        )
