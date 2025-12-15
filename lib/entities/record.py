from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    pass


class RecordStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EDITED = "edited"


class RecordCreate(BaseModel):
    """record data for creation (no id, timestamps added by database)"""

    output: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: RecordStatus = RecordStatus.PENDING
    trace: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("trace", mode="before")
    @classmethod
    def validate_trace(cls, v: list[Any] | None) -> list[dict[str, Any]]:
        """convert None or TraceEntry objects to list of dicts for database compatibility"""
        if v is None:
            return []
        result = []
        for item in v:
            if isinstance(item, dict):
                result.append(item)
            elif hasattr(item, "model_dump"):
                # handle TraceEntry or any pydantic model
                result.append(item.model_dump())
            else:
                result.append(item)
        return result


class Record(RecordCreate):
    """record retrieved from database (has id and timestamps)"""

    id: int
    created_at: datetime
    updated_at: datetime


class RecordUpdate(BaseModel):
    model_config = {"extra": "allow"}
    output: str | None = None
    status: RecordStatus | None = None
    metadata: dict[str, Any] | None = None
