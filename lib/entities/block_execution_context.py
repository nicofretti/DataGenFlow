from typing import Any

from pydantic import BaseModel, Field

from lib.entities.pipeline import Constraints, Usage


class BlockExecutionContext(BaseModel):
    """
    execution context passed to blocks during pipeline execution.

    provides complete execution state for block implementations, eliminating
    the need for None checks and making execution semantics explicit.

    ## Execution Model

    **Trace Hierarchy:**
    - trace_id: unique identifier per execution (single pipeline run)
    - job_id: 0 for direct API calls, >0 for background batch jobs
    - pipeline_id: identifies which pipeline template is executing

    **Sentinel Values:**
    - job_id=0 means direct API call (not a background job)
    - job_id>0 means background job execution
    - This eliminates `if job_id:` checks (use `if job_id > 0:` instead)

    **State Management:**
    - accumulated_state: dict of all outputs from previous blocks in pipeline
    - usage: cumulative LLM token usage (input, output, cached)
    - trace: execution history with inputs/outputs of each block
    - constraints: pipeline limits (max tokens, execution time)

    ## Usage Example

    ```python
    async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
        # access previous block outputs
        user_text = context.get_state("user", "")

        # check if running in background job
        if context.job_id > 0:
            # add job-specific logic
            pass

        # trace_id always present (no None check needed)
        metadata = {"trace_id": context.trace_id}

        return {"result": "..."}
    ```
    """

    trace_id: str = Field(..., description="unique execution identifier")
    job_id: int = Field(0, description="0 = direct API call, >0 = background job id")
    pipeline_id: int = Field(..., description="pipeline identifier")
    accumulated_state: dict[str, Any] = Field(
        default_factory=dict, description="outputs from previous blocks"
    )
    usage: Usage = Field(default_factory=Usage, description="cumulative token usage")
    trace: list[dict[str, Any]] = Field(
        default_factory=list, description="execution history up to this block"
    )
    constraints: Constraints = Field(
        default_factory=Constraints, description="pipeline execution limits"
    )

    def get_state(self, key: str, default: Any = None) -> Any:
        """safely get field from accumulated_state with default fallback"""
        return self.accumulated_state.get(key, default)

    def update(self, other: dict[str, Any]) -> None:
        """update accumulated_state with new outputs"""
        self.accumulated_state.update(other)

    def copy(self) -> dict[str, Any]:
        """return dict representation for trace snapshots"""
        return {
            "trace_id": self.trace_id,
            "job_id": self.job_id,
            "pipeline_id": self.pipeline_id,
            **self.accumulated_state,
        }
