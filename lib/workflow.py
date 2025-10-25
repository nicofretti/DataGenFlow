import logging
import time
import uuid
from typing import Any

from lib.blocks.registry import registry
from lib.errors import BlockExecutionError, BlockNotFoundError, ValidationError

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, name: str, blocks: list[dict[str, Any]]) -> None:
        self.name = name
        self.blocks = blocks
        self._block_instances: list[Any] = []
        self._initialize_blocks()

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

    @classmethod
    def load_from_dict(cls, data: dict[str, Any]) -> "Pipeline":
        return cls(name=data["name"], blocks=data["blocks"])

    def _validate_output(self, block: Any, result: dict[str, Any]) -> None:
        # validate block returns only declared outputs
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

            # update job status with current block
            if job_id and job_queue:
                job_queue.update_job(
                    job_id,
                    current_block=block_name,
                    current_step=f"Block {i + 1}/{len(self._block_instances)}",
                )
                if storage:
                    await storage.update_job(
                        job_id,
                        current_block=block_name,
                        current_step=f"Block {i + 1}/{len(self._block_instances)}",
                    )

            start_time = time.time()
            try:
                block_input = accumulated_data.copy()
                result = await block.execute(accumulated_data)
                execution_time = time.time() - start_time

                logger.debug(f"[{trace_id}] {block_name} completed in {execution_time:.3f}s")

                # validate output matches declared schema
                self._validate_output(block, result)

                # merge result into accumulated data
                accumulated_data.update(result)

                # capture trace with accumulated state
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
                # wrap execution errors with context
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

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "blocks": self.blocks}
