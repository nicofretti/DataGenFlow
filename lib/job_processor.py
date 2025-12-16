import asyncio
import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from lib.entities import JobStatus, PipelineDefinition, RecordCreate, pipeline
from lib.job_queue import JobQueue
from lib.storage import Storage
from lib.workflow import Pipeline as WorkflowPipeline


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
            await job_queue.update_and_persist(
                job_id,
                storage,
                status=JobStatus.FAILED,
                error="Pipeline not found",
                completed_at=datetime.now().isoformat(),
            )
            return

        pipeline_obj = WorkflowPipeline.load_from_dict(pipeline_data.definition)

        # load constraints from pipeline using type-safe model
        pipeline_def = PipelineDefinition(**pipeline_data.definition)
        constraints = pipeline_def.constraints

        # initialize usage tracker
        accumulated_usage = pipeline.Usage()

        has_multiplier = len(pipeline_obj._block_instances) > 0 and getattr(
            pipeline_obj._block_instances[0], "is_multiplier", False
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
            if job_status and job_status.status == JobStatus.CANCELLED:
                logger.info(
                    f"[Job {job_id}] Cancelled at execution {execution_index}/{total_executions}"
                )
                break

            repetitions = seed.get("repetitions", 1)
            if not isinstance(repetitions, int):
                repetitions = 1

            metadata = {**seed.get("metadata", {}), "job_id": job_id}

            for _ in range(repetitions):
                execution_index += 1

                job_status = job_queue.get_job(job_id)
                if job_status and job_status.status == JobStatus.CANCELLED:
                    cancel_msg = (
                        f"[Job {job_id}] Cancelled at "
                        f"execution {execution_index}/{total_executions}"
                    )
                    logger.info(cancel_msg)
                    break

                try:
                    if has_multiplier:
                        progress = execution_index / total_executions
                        await job_queue.update_and_persist(
                            job_id,
                            storage,
                            current_seed=execution_index,
                            total_seeds=total_executions,
                            progress=progress,
                            current_block=None,
                            current_step=(
                                f"Processing execution {execution_index}/{total_executions}"
                            ),
                        )

                        results = await pipeline_obj.execute(
                            metadata,
                            job_id=job_id,
                            job_queue=job_queue,
                            storage=storage,
                            pipeline_id=pipeline_id,
                            constraints=constraints,
                        )
                        assert isinstance(results, list)
                        # multiplier results already saved in workflow
                        records_generated += len(results)
                        for result_item in results:
                            accumulated_usage.input_tokens += result_item.usage.input_tokens
                            accumulated_usage.output_tokens += result_item.usage.output_tokens
                            accumulated_usage.cached_tokens += result_item.usage.cached_tokens

                        # update usage after processing multiplier seed
                        logger.info(
                            f"[Job {job_id}] Updating usage: "
                            f"in={accumulated_usage.input_tokens}, "
                            f"out={accumulated_usage.output_tokens}, "
                            f"cached={accumulated_usage.cached_tokens}"
                        )
                        await job_queue.update_and_persist(
                            job_id,
                            storage,
                            records_generated=records_generated,
                            usage=accumulated_usage,
                        )
                    else:
                        progress = execution_index / total_executions
                        await job_queue.update_and_persist(
                            job_id,
                            storage,
                            current_seed=execution_index,
                            total_seeds=total_executions,
                            progress=progress,
                            current_block=None,
                            current_step=(
                                f"Processing execution {execution_index}/{total_executions}"
                            ),
                        )

                        result = await pipeline_obj.execute(
                            metadata,
                            job_id=job_id,
                            job_queue=job_queue,
                            storage=storage,
                            pipeline_id=pipeline_id,
                            constraints=constraints,
                        )
                        assert isinstance(result, pipeline.ExecutionResult)
                        exec_result: pipeline.ExecutionResult = result

                        # extract usage from result
                        accumulated_usage.input_tokens += exec_result.usage.input_tokens
                        accumulated_usage.output_tokens += exec_result.usage.output_tokens
                        accumulated_usage.cached_tokens += exec_result.usage.cached_tokens

                        record = RecordCreate(
                            metadata=metadata,
                            output=json.dumps(exec_result.result),
                            trace=exec_result.trace,
                        )

                        await storage.save_record(record, pipeline_id=pipeline_id, job_id=job_id)
                        records_generated += 1

                        logger.info(
                            f"[Job {job_id}] Updating usage: "
                            f"in={accumulated_usage.input_tokens}, "
                            f"out={accumulated_usage.output_tokens}, "
                            f"cached={accumulated_usage.cached_tokens}"
                        )
                        await job_queue.update_and_persist(
                            job_id,
                            storage,
                            records_generated=records_generated,
                            usage=accumulated_usage,
                        )

                    # constraint checking for normal pipelines
                    # note: multiplier pipelines check constraints in workflow.py
                    # both paths use Constraints.is_exceeded() for consistency
                    # check constraints after each execution
                    if not constraints:
                        continue

                    exceeded, constraint_name = constraints.is_exceeded(accumulated_usage)
                    if not exceeded:
                        continue

                    logger.info(f"[Job {job_id}] stopped: {constraint_name} exceeded")
                    accumulated_usage.end_time = time.time()
                    await job_queue.update_and_persist(
                        job_id,
                        storage,
                        status=JobStatus.STOPPED,
                        completed_at=datetime.now().isoformat(),
                        usage=accumulated_usage,
                        error=f"Constraint exceeded: {constraint_name}",
                    )
                    break

                except Exception as e:
                    records_failed += 1
                    error_msg = str(e)
                    logger.error(f"[Job {job_id}] Execution {execution_index} failed: {e}")

                    await job_queue.update_and_persist(
                        job_id,
                        storage,
                        records_failed=records_failed,
                        error=error_msg,
                    )

                    continue

            # check if job was cancelled or stopped in inner loop
            # this is critical: the inner loop (repetitions) has break statements for cancellation
            # but break only exits the inner loop, not the outer loop (seeds)
            # without this check, cancellation would only stop current seed's repetitions,
            # then continue processing remaining seeds - job would keep running!
            job_status = job_queue.get_job(job_id)
            if job_status and job_status.status in (
                JobStatus.CANCELLED,
                JobStatus.STOPPED,
            ):
                logger.info(f"[Job {job_id}] Stopping seed processing: status={job_status.status}")
                break

        try:
            seed_path.unlink()
        except Exception as e:
            logger.warning(f"failed to delete seed file {seed_path}: {e}")

        final_status = job_queue.get_job(job_id)
        if final_status and final_status.status not in (
            JobStatus.CANCELLED,
            JobStatus.STOPPED,
        ):
            accumulated_usage.end_time = time.time()
            completed_at = datetime.now().isoformat()
            await job_queue.update_and_persist(
                job_id,
                storage,
                status=JobStatus.COMPLETED,
                progress=1.0,
                completed_at=completed_at,
                usage=accumulated_usage,
            )
            logger.info(
                f"[Job {job_id}] Completed: {records_generated} generated, {records_failed} failed"
            )

    except Exception as e:
        logger.exception(f"[Job {job_id}] Failed")
        error_msg = str(e)

        completed_at = datetime.now().isoformat()
        await job_queue.update_and_persist(
            job_id,
            storage,
            status=JobStatus.FAILED,
            error=error_msg,
            completed_at=completed_at,
        )
