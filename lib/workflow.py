import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any

from lib.blocks.registry import registry
from lib.entities import JobStatus, RecordCreate, TraceEntry, pipeline
from lib.entities.block_execution_context import BlockExecutionContext
from lib.errors import BlockExecutionError, BlockNotFoundError, ValidationError

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, name: str, blocks: list[dict[str, Any]]) -> None:
        self.name = name
        self.blocks = blocks
        self._block_instances: list[Any] = []
        self._initialize_blocks()
        self._validate_multiplier_placement()

    async def _update_job_progress(
        self, job_id: int | None, job_queue: Any, storage: Any, **updates: Any
    ) -> None:
        """helper to update job progress in both memory and database"""
        if not job_id or not job_queue:
            return

        await job_queue.update_and_persist(job_id, storage, **updates)

    def _initialize_blocks(self) -> None:
        for block_def in self.blocks:
            block_type = block_def["type"]
            block_config = block_def.get("config", {})

            block_class = registry.get_block_class(block_type)
            if not block_class:
                available = list(registry._blocks.keys())
                raise BlockNotFoundError(
                    f"Block '{block_type}' not found",
                    detail={"block_type": block_type, "available_blocks": available},
                )

            self._block_instances.append(block_class(**block_config))

    def _validate_multiplier_placement(self) -> None:
        multiplier_indices = [
            i
            for i, block in enumerate(self._block_instances)
            if getattr(block, "is_multiplier", False)
        ]

        if len(multiplier_indices) > 1:
            raise ValidationError("Only one multiplier block allowed per pipeline")

        if multiplier_indices and multiplier_indices[0] != 0:
            raise ValidationError("Multiplier block must be first in pipeline")

    @classmethod
    def load_from_dict(cls, data: dict[str, Any]) -> "Pipeline":
        return cls(name=data["name"], blocks=data["blocks"])

    def _validate_output(self, block: Any, result: dict[str, Any]) -> None:
        declared = set(block.outputs)
        actual = set(result.keys())

        # skip validation if block declares "*" (any outputs allowed)
        if "*" in declared:
            return

        if not actual.issubset(declared):
            extra = actual - declared
            raise ValidationError(
                f"Block '{block.__class__.__name__}' returned undeclared fields: {extra}",
                detail={
                    "block_type": block.__class__.__name__,
                    "declared_outputs": list(declared),
                    "actual_outputs": list(actual),
                    "extra_fields": list(extra),
                },
            )

    async def execute(
        self,
        initial_data: dict[str, Any],
        job_id: int = 0,
        job_queue: Any = None,
        storage: Any = None,
        pipeline_id: int = 0,
        constraints: pipeline.Constraints = pipeline.Constraints(),
    ) -> pipeline.ExecutionResult | list[pipeline.ExecutionResult]:
        trace_id = str(uuid.uuid4())

        if not self._block_instances:
            return pipeline.ExecutionResult(
                result=initial_data, trace=[], trace_id=trace_id, usage=pipeline.Usage()
            )

        first_block = self._block_instances[0]
        is_multiplier = getattr(first_block, "is_multiplier", False)

        if is_multiplier:
            return await self._execute_multiplier_pipeline(
                initial_data, job_id, job_queue, storage, pipeline_id, constraints
            )

        return await self._execute_normal_pipeline(
            initial_data, job_id, job_queue, storage, pipeline_id, constraints
        )

    async def _execute_normal_pipeline(
        self,
        initial_data: dict[str, Any],
        job_id: int = 0,
        job_queue: Any = None,
        storage: Any = None,
        pipeline_id: int = 0,
        constraints: pipeline.Constraints = pipeline.Constraints(),
    ) -> pipeline.ExecutionResult:
        context = BlockExecutionContext(
            trace_id=initial_data.get("trace_id", str(uuid.uuid4())),
            job_id=job_id,
            pipeline_id=pipeline_id,
            accumulated_state=initial_data.copy(),
            usage=pipeline.Usage(),
            trace=[],
            constraints=constraints,
        )

        block_count = len(self._block_instances)
        logger.info(
            f"[{context.trace_id}] Starting pipeline '{self.name}' with {block_count} blocks"
        )

        for i, block in enumerate(self._block_instances):
            # check if job was cancelled before executing next block
            if job_id > 0 and job_queue:
                job_status = job_queue.get_job(job_id)
                if job_status and job_status.status == JobStatus.CANCELLED:
                    total_blocks = len(self._block_instances)
                    msg = (
                        f"[{context.trace_id}] Job {job_id} cancelled "
                        f"at block {i + 1}/{total_blocks}"
                    )
                    logger.info(msg)
                    # return partial result with what we've executed so far
                    return pipeline.ExecutionResult(
                        result=context.accumulated_state,
                        trace=context.trace,
                        trace_id=context.trace_id,
                        usage=context.usage,
                    )

            block_name = block.__class__.__name__
            total = len(self._block_instances)
            logger.debug(f"[{context.trace_id}] Executing block {i + 1}/{total}: {block_name}")

            await self._update_job_progress(
                job_id,
                job_queue,
                storage,
                current_block=block_name,
                current_step=f"Block {i + 1}/{len(self._block_instances)}",
            )

            start_time = time.time()
            try:
                block_input = context.accumulated_state.copy()
                result = await block.execute(context)
                execution_time = time.time() - start_time

                logger.debug(
                    f"[{context.trace_id}] {block_name} completed in {execution_time:.3f}s"
                )

                # extract usage if present
                if "_usage" in result:
                    try:
                        block_usage = pipeline.Usage(**result.pop("_usage"))
                        context.usage.input_tokens += block_usage.input_tokens
                        context.usage.output_tokens += block_usage.output_tokens
                        context.usage.cached_tokens += block_usage.cached_tokens
                    except (ValueError, KeyError) as e:
                        # log but don't fail - block didn't return valid usage
                        logger.warning(f"Invalid usage from {block_name}: {e}")
                        result.pop("_usage", None)

                self._validate_output(block, result)
                context.update(result)

                context.trace.append(
                    TraceEntry(
                        block_type=block_name,
                        input=block_input,
                        output=result,
                        accumulated_state=context.accumulated_state.copy(),
                        execution_time=execution_time,
                    )
                )
            except ValidationError:
                # re-raise validation errors as-is
                logger.error(f"[{context.trace_id}] {block_name} validation error at step {i + 1}")
                raise
            except Exception as e:
                logger.exception(f"[{context.trace_id}] {block_name} failed at step {i + 1}")
                raise BlockExecutionError(
                    f"Block '{block_name}' failed at step {i + 1}: {str(e)}",
                    detail={
                        "block_type": block_name,
                        "step": i + 1,
                        "error": str(e),
                        "input": block_input,
                    },
                )

        logger.info(f"[{context.trace_id}] Pipeline '{self.name}' completed successfully")
        return pipeline.ExecutionResult(
            result=context.accumulated_state,
            trace=context.trace,
            trace_id=context.trace_id,
            usage=context.usage,
        )

    async def _execute_block_in_seed(
        self,
        block: Any,
        context: BlockExecutionContext,
        seed_idx: int,
    ) -> None:
        """execute single block within seed processing"""
        block_name = block.__class__.__name__
        block_start_time = time.time()
        block_input = context.accumulated_state.copy()

        try:
            result = await block.execute(context)
            block_execution_time = time.time() - block_start_time

            # extract usage if present
            if "_usage" in result:
                try:
                    block_usage = pipeline.Usage(**result.pop("_usage"))
                    context.usage.input_tokens += block_usage.input_tokens
                    context.usage.output_tokens += block_usage.output_tokens
                    context.usage.cached_tokens += block_usage.cached_tokens
                except (ValueError, KeyError) as e:
                    logger.warning(f"Invalid usage from {block_name}: {e}")
                    result.pop("_usage", None)

            self._validate_output(block, result)
            context.update(result)
            context.trace.append(
                TraceEntry(
                    block_type=block_name,
                    input=block_input,
                    output=result,
                    accumulated_state=context.accumulated_state.copy(),
                    execution_time=block_execution_time,
                )
            )
        except Exception as e:
            logger.exception(f"[{context.trace_id}] {block_name} failed at seed {seed_idx + 1}")
            context.trace.append(
                TraceEntry(
                    block_type=block_name,
                    input=block_input,
                    output=None,
                    error=str(e),
                )
            )
            raise

    async def _save_seed_result(
        self,
        initial_data: dict[str, Any],
        accumulated_data: dict[str, Any],
        trace: list[TraceEntry],
        pipeline_id: int,
        job_id: int,
        job_queue: Any,
        storage: Any,
    ) -> None:
        """save completed seed result and update counters"""
        record = RecordCreate(
            metadata=initial_data, output=json.dumps(accumulated_data), trace=trace
        )
        await storage.save_record(record, pipeline_id=pipeline_id, job_id=job_id)

        if not job_queue:
            return

        current_job = job_queue.get_job(job_id)
        if not current_job:
            return

        await self._update_job_progress(
            job_id,
            job_queue,
            storage,
            records_generated=current_job.records_generated + 1,
        )

    async def _process_single_seed(
        self,
        seed_idx: int,
        seed_data: dict[str, Any],
        remaining_blocks: list[Any],
        initial_data: dict[str, Any],
        job_id: int,
        job_queue: Any,
        storage: Any,
        pipeline_id: int,
        total_seeds: int,
        constraints: pipeline.Constraints,
    ) -> pipeline.ExecutionResult | None:
        """process one seed through all remaining blocks"""
        # create execution context for this seed
        context = BlockExecutionContext(
            trace_id=str(uuid.uuid4()),
            job_id=job_id,
            pipeline_id=pipeline_id,
            accumulated_state=seed_data.copy(),
            usage=pipeline.Usage(),
            trace=[],
            constraints=constraints,
        )

        try:
            for i, block in enumerate(remaining_blocks, start=1):
                # check if job was cancelled before executing next block
                if job_id > 0 and job_queue:
                    job_status = job_queue.get_job(job_id)
                    if job_status and job_status.status == JobStatus.CANCELLED:
                        total_remaining = len(remaining_blocks)
                        logger.info(
                            f"[{context.trace_id}] Job {job_id} cancelled at seed "
                            f"{seed_idx + 1}, block {i}/{total_remaining}"
                        )
                        return None

                progress = seed_idx / total_seeds if total_seeds > 0 else 0.0
                step = f"Seed {seed_idx + 1}/{total_seeds}, Block {i}/{len(remaining_blocks)}"
                await self._update_job_progress(
                    job_id,
                    job_queue,
                    storage,
                    current_seed=seed_idx + 1,
                    progress=progress,
                    current_block=block.__class__.__name__,
                    current_step=step,
                )
                await self._execute_block_in_seed(block, context, seed_idx)

            if storage and pipeline_id > 0 and job_id > 0:
                await self._save_seed_result(
                    initial_data,
                    context.accumulated_state,
                    context.trace,
                    pipeline_id,
                    job_id,
                    job_queue,
                    storage,
                )

                # update cumulative usage in job after each seed
                if not job_queue:
                    return pipeline.ExecutionResult(
                        result=context.accumulated_state,
                        trace=context.trace,
                        trace_id=context.trace_id,
                        usage=context.usage,
                    )

                current_job = job_queue.get_job(job_id)
                if not current_job:
                    return pipeline.ExecutionResult(
                        result=context.accumulated_state,
                        trace=context.trace,
                        trace_id=context.trace_id,
                        usage=context.usage,
                    )

                # get current cumulative usage and add this seed's usage
                usage_model = current_job.usage
                usage_model.input_tokens += context.usage.input_tokens
                usage_model.output_tokens += context.usage.output_tokens
                usage_model.cached_tokens += context.usage.cached_tokens

                await self._update_job_progress(
                    job_id,
                    job_queue,
                    storage,
                    usage=usage_model,
                )
                logger.info(
                    f"[Job {job_id}] Updated usage after seed "
                    f"{seed_idx + 1}/{total_seeds}: "
                    f"in={usage_model.input_tokens}, "
                    f"out={usage_model.output_tokens}, "
                    f"cached={usage_model.cached_tokens}"
                )

            return pipeline.ExecutionResult(
                result=context.accumulated_state,
                trace=context.trace,
                trace_id=context.trace_id,
                usage=context.usage,
            )
        except Exception:
            logger.exception(f"[{context.trace_id}] Seed {seed_idx + 1}/{total_seeds} failed")

            if job_id == 0 or not job_queue:
                return None

            current_job = job_queue.get_job(job_id)
            if not current_job:
                return None

            await self._update_job_progress(
                job_id,
                job_queue,
                storage,
                records_failed=current_job.records_failed + 1,
            )
            return None
        finally:
            progress = (seed_idx + 1) / total_seeds if total_seeds > 0 else 0.0
            status_msg = (
                f"Completed seed {seed_idx + 1}/{total_seeds}"
                if context.accumulated_state
                else f"Failed seed {seed_idx + 1}/{total_seeds}"
            )
            await self._update_job_progress(
                job_id,
                job_queue,
                storage,
                current_seed=seed_idx + 1,
                progress=progress,
                current_block=None,
                current_step=status_msg,
            )

    async def _execute_multiplier_pipeline(
        self,
        initial_data: dict[str, Any],
        job_id: int = 0,
        job_queue: Any = None,
        storage: Any = None,
        pipeline_id: int = 0,
        constraints: pipeline.Constraints = pipeline.Constraints(),
    ) -> list[pipeline.ExecutionResult]:
        """execute pipeline with multiplier first block that generates multiple seeds"""
        first_block = self._block_instances[0]
        remaining_blocks = self._block_instances[1:]

        context = BlockExecutionContext(
            trace_id=str(uuid.uuid4()),
            job_id=job_id,
            pipeline_id=pipeline_id,
            accumulated_state=initial_data.copy(),
            usage=pipeline.Usage(),
            trace=[],
            constraints=constraints,
        )

        logger.info(f"Starting multiplier pipeline '{self.name}' with fan-out")
        start_time = time.time()
        seeds = await first_block.execute(context)
        logger.info(
            f"Multiplier block generated {len(seeds)} seeds in {time.time() - start_time:.3f}s"
        )

        await self._update_job_progress(
            job_id, job_queue, storage, total_seeds=len(seeds), current_seed=0
        )

        results = []
        for seed_idx, seed_data in enumerate(seeds):
            # check if job was cancelled before processing next seed
            if job_id > 0 and job_queue:
                job_status = job_queue.get_job(job_id)
                if job_status and job_status.status == JobStatus.CANCELLED:
                    total_seeds = len(seeds)
                    logger.info(
                        f"[Job {job_id}] Multiplier pipeline cancelled at "
                        f"seed {seed_idx + 1}/{total_seeds}"
                    )
                    break

            result = await self._process_single_seed(
                seed_idx,
                seed_data,
                remaining_blocks,
                initial_data,
                job_id,
                job_queue,
                storage,
                pipeline_id,
                len(seeds),
                constraints,
            )
            if result:
                results.append(result)

            # constraint checking for multiplier pipelines
            # note: normal pipelines check constraints in job_processor.py
            # this is by design - two execution paths,
            # same constraint logic via Constraints.is_exceeded()
            # check constraints after each seed
            if job_id == 0 or not job_queue:
                continue

            current_job = job_queue.get_job(job_id)
            if not current_job:
                continue

            # usage is already a Usage object
            try:
                exceeded, constraint_name = constraints.is_exceeded(current_job.usage)
                if not exceeded:
                    continue

                logger.info(
                    f"[Job {job_id}] Multiplier pipeline stopped: {constraint_name} exceeded"
                )
                current_job.usage.end_time = time.time()

                await self._update_job_progress(
                    job_id,
                    job_queue,
                    storage,
                    status=JobStatus.STOPPED,
                    completed_at=datetime.now().isoformat(),
                    usage=current_job.usage,
                    error=f"Constraint exceeded: {constraint_name}",
                )
                break
            except (ValueError, KeyError, json.JSONDecodeError) as e:
                logger.warning(f"Failed to check constraints for job {job_id}: {e}")

        logger.info(f"Multiplier pipeline '{self.name}' completed with {len(results)} results")
        return results

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "blocks": self.blocks}
