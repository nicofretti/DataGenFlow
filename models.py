from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RecordStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EDITED = "edited"


class BlockDefinition(BaseModel):
    type: str
    config: dict[str, Any] = Field(default_factory=dict)


class Pipeline(BaseModel):
    name: str
    blocks: list[BlockDefinition]


class SeedInput(BaseModel):
    repetitions: int = Field(default=1, description="Number of times to execute pipeline")
    metadata: dict[str, Any] = Field(..., description="Variables for pipeline execution")


class Record(BaseModel):
    id: int | None = None
    output: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: RecordStatus = RecordStatus.PENDING
    trace: list[dict[str, Any]] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class GenerationConfig(BaseModel):
    model: str | None = None
    endpoint: str | None = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1)


class RecordUpdate(BaseModel):
    output: str | None = None
    status: RecordStatus | None = None
    metadata: dict[str, Any] | None = None
