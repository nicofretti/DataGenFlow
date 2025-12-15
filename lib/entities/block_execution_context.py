from typing import Any

from pydantic import BaseModel, Field

from lib.entities.pipeline import Constraints, TraceEntry, Usage


class BlockExecutionContext(BaseModel):
    """
    execution context passed to blocks during pipeline execution.

    provides full visibility into execution state for advanced block logic:
    - trace_id: unique identifier for this execution (for observability)
    - job_id: 0 for direct API calls, >0 for background jobs
    - pipeline_id: which pipeline this execution belongs to
    - accumulated_state: all outputs from previous blocks
    - usage: cumulative token usage up to this point
    - trace: execution history of all previous blocks
    - constraints: pipeline execution limits (tokens, time)
    """

    trace_id: str = Field(..., description="unique execution identifier")
    job_id: int = Field(0, description="0 = direct API call, >0 = background job id")
    pipeline_id: int = Field(..., description="pipeline identifier")
    accumulated_state: dict[str, Any] = Field(
        default_factory=dict, description="outputs from previous blocks"
    )
    usage: Usage = Field(default_factory=Usage, description="cumulative token usage")
    trace: list[TraceEntry] = Field(
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

    def copy(self) -> dict[str, Any]:  # type: ignore[override]
        """return dict representation for trace snapshots"""
        return {
            "trace_id": self.trace_id,
            "job_id": self.job_id,
            "pipeline_id": self.pipeline_id,
            **self.accumulated_state,
        }
