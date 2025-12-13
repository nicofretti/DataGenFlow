from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, field_validator

class RecordStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EDITED = "edited"

class Record(BaseModel):
    id: int | None = None
    output: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: RecordStatus = RecordStatus.PENDING
    trace: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("trace", mode="before")
    @classmethod
    def validate_trace(cls, v: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
        return v if v is not None else []

class RecordUpdate(BaseModel):
    model_config = {"extra": "allow"}
    output: str | None = None
    status: RecordStatus | None = None
    metadata: dict[str, Any] | None = None
