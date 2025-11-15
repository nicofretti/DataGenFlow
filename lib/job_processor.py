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
        # give litellm's background logging tasks time to complete
        pending = asyncio.all_tasks(loop)
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    except Exception as e:
        logger.error(f"Job thread failed: {e}")
    finally:
        # properly shutdown async generators before closing
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        except Exception as e:
            logger.warning(f"failed to shutdown async generators: {e}")
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

        has_multiplier = len(pipeline._block_instances) > 0 and getattr(
            pipeline._block_instances[0], "is_multiplier", False
        )

        seed_path = Path(seed_file_path)
        if not seed_path.exists():
            raise FileNotFoundError(f"Seed file not found: {seed_file_path}")

        def _read_seed_file() -> Any:
            with open(seed_path, "r", encoding="utf-8") as f:
                return json.load(f)

        data = await asyncio.to_thread(_read_seed_file)

        seeds_data = data if isinstance(data, list) else [data]

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

        for seed in seeds_data:
            job_status = job_queue.get_job(job_id)
            if job_status and job_status.get("status") == "cancelled":
                logger.info(
                    f"[Job {job_id}] Cancelled at execution {execution_index}/{total_executions}"
                )
                break

            repetitions = seed.get("repetitions", 1)
            if not isinstance(repetitions, int):
                repetitions = 1

            metadata = seed.get("metadata", {})

            for i in range(repetitions):
                execution_index += 1

                job_status = job_queue.get_job(job_id)
                if job_status and job_status.get("status") == "cancelled":
                    cancel_msg = (
                        f"[Job {job_id}] Cancelled at "
                        f"execution {execution_index}/{total_executions}"
                    )
                    logger.info(cancel_msg)
                    break

                try:
                    if has_multiplier:
                        results = await pipeline.execute(
                            metadata,
                            job_id=job_id,
                            job_queue=job_queue,
                            storage=storage,
                            pipeline_id=pipeline_id,
                        )
                        assert isinstance(results, list)
                    else:
                        progress = execution_index / total_executions
                        await _update_job_status(
                            job_queue,
                            storage,
                            job_id,
                            current_seed=execution_index,
                            total_seeds=total_executions,
                            progress=progress,
                            current_block=None,
                            current_step=(
                                f"Processing execution {execution_index}/{total_executions}"
                            ),
                        )

                        exec_result = await pipeline.execute(
                            metadata,
                            job_id=job_id,
                            job_queue=job_queue,
                            storage=storage,
                            pipeline_id=pipeline_id,
                        )
                        assert isinstance(exec_result, tuple)
                        result, trace, trace_id = exec_result

                        record = Record(
                            metadata=metadata,
                            output=json.dumps(result),
                            trace=trace,
                        )

                        await storage.save_record(record, pipeline_id=pipeline_id, job_id=job_id)
                        records_generated += 1

                        await _update_job_status(
                            job_queue,
                            storage,
                            job_id,
                            records_generated=records_generated,
                        )

                except Exception as e:
                    records_failed += 1
                    error_msg = str(e)
                    logger.error(f"[Job {job_id}] Execution {execution_index} failed: {e}")

                    await _update_job_status(
                        job_queue, storage, job_id, records_failed=records_failed, error=error_msg
                    )

                    continue

        try:
            seed_path.unlink()
        except Exception as e:
            logger.warning(f"failed to delete seed file {seed_path}: {e}")

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
        logger.exception(f"[Job {job_id}] Failed")
        error_msg = str(e)

        completed_at = datetime.now().isoformat()
        await _update_job_status(
            job_queue,
            storage,
            job_id,
            status="failed",
            error=error_msg,
            completed_at=completed_at,
        )
