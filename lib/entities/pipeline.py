import time
from typing import Any

from pydantic import BaseModel, Field, field_validator


class TraceEntry(BaseModel):
    """single entry in execution trace"""

    block_type: str
    input: dict[str, Any]
    output: dict[str, Any] | None = None
    accumulated_state: dict[str, Any] | None = None
    execution_time: float | None = None
    error: str | None = None


class ExecutionResult(BaseModel):
    """
    result of a single pipeline execution.

    conceptual hierarchy:
    - job: batch of multiple executions (e.g., 100 generated records)
    - execution: single pipeline run producing one record (this object)
    - trace_id: unique identifier for this execution, used for grouping
      related LLM calls in observability tools

    for langfuse integration:
    - trace_id groups all LLM calls from this execution
    - multiple executions (traces) belong to the same job
    - example: job with 10 repetitions = 10 ExecutionResults with different trace_ids
    """

    result: dict[str, Any]  # final output data from pipeline
    trace: list[TraceEntry]  # execution history (block inputs/outputs)
    trace_id: str  # unique id for this execution (for observability)
    usage: "Usage"  # token usage for this execution


class Constraints(BaseModel):
    """constraints for pipeline execution. -1 means unlimited."""

    max_total_tokens: int = Field(
        -1,
        ge=-1,
        description="maximum total tokens (sum of input+output+cached), -1 = unlimited",
    )
    max_total_input_tokens: int = Field(
        -1, ge=-1, description="maximum input tokens, -1 = unlimited"
    )
    max_total_output_tokens: int = Field(
        -1, ge=-1, description="maximum output tokens, -1 = unlimited"
    )
    max_total_cached_tokens: int = Field(
        -1, ge=-1, description="maximum cached tokens, -1 = unlimited"
    )
    max_total_execution_time: int = Field(
        -1, ge=-1, description="maximum execution time in seconds, -1 = unlimited"
    )

    @field_validator(
        "max_total_tokens",
        "max_total_input_tokens",
        "max_total_output_tokens",
        "max_total_cached_tokens",
        "max_total_execution_time",
        mode="before",
    )
    @classmethod
    def validate_constraint_fields(cls, v: int | None) -> int:
        """convert None to -1 for database compatibility"""
        return -1 if v is None else v

    def is_exceeded(self, usage: "Usage") -> tuple[bool, str | None]:
        """check if any constraint is exceeded. returns (exceeded, constraint_name)."""
        checks = [
            (self.max_total_tokens, usage.total_tokens, "max_total_tokens"),
            (self.max_total_input_tokens, usage.input_tokens, "max_total_input_tokens"),
            (
                self.max_total_output_tokens,
                usage.output_tokens,
                "max_total_output_tokens",
            ),
            (
                self.max_total_cached_tokens,
                usage.cached_tokens,
                "max_total_cached_tokens",
            ),
            (
                self.max_total_execution_time,
                usage.elapsed_time,
                "max_total_execution_time",
            ),
        ]

        for limit, current, name in checks:
            if limit >= 0 and current >= limit:
                return True, name
        return False, None


class Usage(BaseModel):
    """token usage information with timing."""

    input_tokens: int = Field(0, ge=0)
    output_tokens: int = Field(0, ge=0)
    cached_tokens: int = Field(0, ge=0)
    start_time: float = Field(default_factory=time.time)
    end_time: float | None = Field(None)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens + self.cached_tokens

    @property
    def elapsed_time(self) -> float:
        """calculate elapsed time (end_time - start_time, or current - start_time if not ended)"""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time


class FieldOrder(BaseModel):
    """field ordering configuration for validation ui."""

    primary: list[str] = Field(default_factory=list)
    secondary: list[str] = Field(default_factory=list)
    hidden: list[str] = Field(default_factory=list)


class ValidationConfig(BaseModel):
    """validation configuration for pipeline records."""

    field_order: FieldOrder


class BlockDefinition(BaseModel):
    type: str
    config: dict[str, Any] = Field(default_factory=dict)


class Pipeline(BaseModel):
    name: str
    blocks: list[BlockDefinition]


class PipelineDefinition(BaseModel):
    """pipeline definition with type-safe constraints parsing"""

    blocks: list[BlockDefinition] = Field(default_factory=list)
    constraints: Constraints = Field(default_factory=Constraints)

    @field_validator("constraints", mode="before")
    @classmethod
    def validate_constraints(cls, v: dict[str, Any] | Constraints | None) -> Constraints:
        """safely parse constraints from dict or None"""
        if v is None:
            return Constraints()
        if isinstance(v, Constraints):
            return v
        return Constraints(**v)


class SeedInput(BaseModel):
    repetitions: int = Field(default=1, description="Number of times to execute pipeline")
    metadata: dict[str, Any] = Field(..., description="Variables for pipeline execution")
