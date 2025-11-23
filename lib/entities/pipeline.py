import time
from typing import Any

from pydantic import BaseModel, Field


class ExecutionResult(BaseModel):
    """result of pipeline execution with usage tracking"""

    result: dict[str, Any]
    trace: list[dict[str, Any]]
    trace_id: str
    usage: dict[str, Any]


class Constraints(BaseModel):
    """constraints for pipeline execution. all fields optional."""

    max_total_tokens: int | None = Field(
        None, ge=0, description="maximum total tokens (sum of input+output+cached)"
    )
    max_total_input_tokens: int | None = Field(None, ge=0, description="maximum input tokens")
    max_total_output_tokens: int | None = Field(None, ge=0, description="maximum output tokens")
    max_total_cached_tokens: int | None = Field(None, ge=0, description="maximum cached tokens")
    max_total_execution_time: int | None = Field(
        None, ge=0, description="maximum execution time in seconds"
    )

    def is_exceeded(self, usage: "Usage") -> tuple[bool, str | None]:
        """check if any constraint is exceeded. returns (exceeded, constraint_name)."""
        checks = [
            (self.max_total_tokens, usage.total_tokens, "max_total_tokens"),
            (self.max_total_input_tokens, usage.input_tokens, "max_total_input_tokens"),
            (self.max_total_output_tokens, usage.output_tokens, "max_total_output_tokens"),
            (self.max_total_cached_tokens, usage.cached_tokens, "max_total_cached_tokens"),
            (self.max_total_execution_time, usage.elapsed_time, "max_total_execution_time"),
        ]

        for limit, current, name in checks:
            if limit is not None and current >= limit:
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
