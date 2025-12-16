from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from lib.entities.pipeline import Usage


class JobStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STOPPED = "stopped"


TERMINAL_STATUSES = {
    JobStatus.COMPLETED,
    JobStatus.FAILED,
    JobStatus.CANCELLED,
    JobStatus.STOPPED,
}


class Job(BaseModel):
    """job record from database"""

    id: int
    pipeline_id: int
    status: JobStatus
    total_seeds: int
    current_seed: int = 0
    records_generated: int = 0
    records_failed: int = 0
    progress: float = 0.0
    current_block: str = ""
    current_step: str = ""
    error: str = ""
    started_at: str
    completed_at: str | None = None
    created_at: str | None = None
    usage: Usage = Field(default_factory=Usage)
    metadata: str = ""

    @field_validator("current_block", "current_step", "error", "metadata", mode="before")
    @classmethod
    def validate_str_fields(cls, v: str | None) -> str:
        """convert None to empty string for database compatibility"""
        return v if v is not None else ""

    @field_validator("usage", mode="before")
    @classmethod
    def validate_usage(cls, v: Usage | dict[str, Any] | str | None) -> Usage:
        """convert from various formats to Usage object"""
        if v is None:
            return Usage()
        if isinstance(v, Usage):
            return v
        if isinstance(v, str):
            import json

            try:
                data = json.loads(v)
                return Usage(**data)
            except (json.JSONDecodeError, ValueError):
                return Usage()
        if isinstance(v, dict):
            return Usage(**v)
        return Usage()
