from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RecordStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EDITED = "edited"


class SeedInput(BaseModel):
    system: str = Field(..., description="System prompt template with {placeholders}")
    user: str = Field(..., description="User prompt template with {placeholders}")
    metadata: dict[str, Any] = Field(..., description="Data to fill templates + num_samples")


class Record(BaseModel):
    id: int | None = None
    system: str
    user: str
    assistant: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: RecordStatus = RecordStatus.PENDING
    created_at: datetime | None = None
    updated_at: datetime | None = None


class GenerationConfig(BaseModel):
    model: str | None = None
    endpoint: str | None = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1)


class RecordUpdate(BaseModel):
    system: str | None = None
    user: str | None = None
    assistant: str | None = None
    status: RecordStatus | None = None
    metadata: dict[str, Any] | None = None
