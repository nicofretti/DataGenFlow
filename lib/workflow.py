import json
import logging
import time
import uuid
from typing import Any

from lib.blocks.registry import registry
from lib.errors import BlockExecutionError, BlockNotFoundError, ValidationError
from models import Record

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

        job_queue.update_job(job_id, **updates)
        if storage:
            await storage.update_job(job_id, **updates)

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
        job_id: int | None = None,
        job_queue: Any = None,
        storage: Any = None,
        pipeline_id: int | None = None,
    ) -> (
        tuple[dict[str, Any], list[dict[str, Any]], str]
        | list[tuple[dict[str, Any], list[dict[str, Any]], str]]
    ):
        if not self._block_instances:
            trace_id = str(uuid.uuid4())
            return initial_data, [], trace_id

        first_block = self._block_instances[0]
        is_multiplier = getattr(first_block, "is_multiplier", False)

        if is_multiplier:
            return await self._execute_multiplier_pipeline(
                initial_data, job_id, job_queue, storage, pipeline_id
            )

        return await self._execute_normal_pipeline(initial_data, job_id, job_queue, storage)

    async def _execute_normal_pipeline(
        self,
        initial_data: dict[str, Any],
        job_id: int | None = None,
        job_queue: Any = None,
        storage: Any = None,
    ) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
        trace_id = str(uuid.uuid4())
        accumulated_data = initial_data.copy()
        trace = []

        logger.info(
            f"[{trace_id}] Starting pipeline '{self.name}' with {len(self._block_instances)} blocks"
        )

        for i, block in enumerate(self._block_instances):
            block_name = block.__class__.__name__
            logger.debug(
                f"[{trace_id}] Executing block {i + 1}/{len(self._block_instances)}: {block_name}"
            )

            await self._update_job_progress(
                job_id,
                job_queue,
                storage,
                current_block=block_name,
                current_step=f"Block {i + 1}/{len(self._block_instances)}",
            )

            start_time = time.time()
            try:
                block_input = accumulated_data.copy()
                result = await block.execute(accumulated_data)
                execution_time = time.time() - start_time

                logger.debug(f"[{trace_id}] {block_name} completed in {execution_time:.3f}s")

                self._validate_output(block, result)
                accumulated_data.update(result)

                trace.append(
                    {
                        "block_type": block_name,
                        "input": block_input,
                        "output": result,
                        "accumulated_state": accumulated_data.copy(),
                        "execution_time": execution_time,
                    }
                )
            except ValidationError:
                # re-raise validation errors as-is
                logger.error(f"[{trace_id}] {block_name} validation error at step {i + 1}")
                raise
            except Exception as e:
                logger.error(f"[{trace_id}] {block_name} failed at step {i + 1}: {str(e)}")
                raise BlockExecutionError(
                    f"Block '{block_name}' failed at step {i + 1}: {str(e)}",
                    detail={
                        "block_type": block_name,
                        "step": i + 1,
                        "error": str(e),
                        "input": block_input,
                    },
                )

        logger.info(f"[{trace_id}] Pipeline '{self.name}' completed successfully")
        return accumulated_data, trace, trace_id

    async def _execute_block_in_seed(
        self,
        block: Any,
        accumulated_data: dict[str, Any],
        trace: list[dict[str, Any]],
        block_idx: int,
        trace_id: str,
        seed_idx: int,
        total_blocks: int,
    ) -> None:
        """execute single block within seed processing"""
        block_name = block.__class__.__name__
        block_start_time = time.time()
        block_input = accumulated_data.copy()

        try:
            result = await block.execute(accumulated_data)
            block_execution_time = time.time() - block_start_time
            self._validate_output(block, result)
            accumulated_data.update(result)
            trace.append(
                {
                    "block_type": block_name,
                    "input": block_input,
                    "output": result,
                    "accumulated_state": accumulated_data.copy(),
                    "execution_time": block_execution_time,
                }
            )
        except Exception as e:
            logger.error(f"[{trace_id}] {block_name} failed at seed {seed_idx + 1}: {str(e)}")
            trace.append(
                {"block_type": block_name, "input": block_input, "output": None, "error": str(e)}
            )
            raise

    async def _save_seed_result(
        self,
        initial_data: dict[str, Any],
        accumulated_data: dict[str, Any],
        trace: list[dict[str, Any]],
        pipeline_id: int,
        job_id: int,
        job_queue: Any,
        storage: Any,
    ) -> None:
        """save completed seed result and update counters"""
        record = Record(metadata=initial_data, output=json.dumps(accumulated_data), trace=trace)
        await storage.save_record(record, pipeline_id=pipeline_id, job_id=job_id)

        if job_queue:
            current_job = job_queue.get_job(job_id)
            if current_job:
                await self._update_job_progress(
                    job_id,
                    job_queue,
                    storage,
                    records_generated=current_job.get("records_generated", 0) + 1,
                )

    async def _process_single_seed(
        self,
        seed_idx: int,
        seed_data: dict[str, Any],
        remaining_blocks: list[Any],
        initial_data: dict[str, Any],
        job_id: int | None,
        job_queue: Any,
        storage: Any,
        pipeline_id: int | None,
        total_seeds: int,
    ) -> tuple[dict[str, Any], list[dict[str, Any]], str] | None:
        """process one seed through all remaining blocks"""
        trace_id = str(uuid.uuid4())
        accumulated_data = seed_data.copy()
        trace: list[dict[str, Any]] = []

        try:
            for i, block in enumerate(remaining_blocks, start=1):
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
                await self._execute_block_in_seed(
                    block, accumulated_data, trace, i, trace_id, seed_idx, len(remaining_blocks)
                )

            if storage and pipeline_id and job_id:
                await self._save_seed_result(
                    initial_data, accumulated_data, trace, pipeline_id, job_id, job_queue, storage
                )

            return (accumulated_data, trace, trace_id)
        except Exception as e:
            logger.error(f"[{trace_id}] Seed {seed_idx + 1}/{total_seeds} failed: {str(e)}")
            if job_id and job_queue:
                current_job = job_queue.get_job(job_id)
                if current_job:
                    await self._update_job_progress(
                        job_id,
                        job_queue,
                        storage,
                        records_failed=current_job.get("records_failed", 0) + 1,
                    )
            return None
        finally:
            progress = (seed_idx + 1) / total_seeds if total_seeds > 0 else 0.0
            status_msg = (
                f"Completed seed {seed_idx + 1}/{total_seeds}"
                if accumulated_data
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
        job_id: int | None = None,
        job_queue: Any = None,
        storage: Any = None,
        pipeline_id: int | None = None,
    ) -> list[tuple[dict[str, Any], list[dict[str, Any]], str]]:
        """execute pipeline with multiplier first block that generates multiple seeds"""
        first_block = self._block_instances[0]
        remaining_blocks = self._block_instances[1:]

        logger.info(f"Starting multiplier pipeline '{self.name}' with fan-out")
        start_time = time.time()
        seeds = await first_block.execute(initial_data)
        logger.info(
            f"Multiplier block generated {len(seeds)} seeds in {time.time() - start_time:.3f}s"
        )

        await self._update_job_progress(
            job_id, job_queue, storage, total_seeds=len(seeds), current_seed=0
        )

        results = []
        for seed_idx, seed_data in enumerate(seeds):
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
            )
            if result:
                results.append(result)

        logger.info(f"Multiplier pipeline '{self.name}' completed with {len(results)} results")
        return results

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "blocks": self.blocks}
