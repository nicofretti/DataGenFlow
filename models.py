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
    output: str | None = None
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
    model_config = {"extra": "allow"}

    output: str | None = None
    status: RecordStatus | None = None
    metadata: dict[str, Any] | None = None


class SeedValidationRequest(BaseModel):
    pipeline_id: int
    seeds: list[dict[str, Any]]


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"


class LLMModelConfig(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    provider: LLMProvider
    endpoint: str | None = None
    api_key: str | None = None
    model_name: str = Field(..., min_length=1)


class EmbeddingModelConfig(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    provider: LLMProvider
    endpoint: str | None = None
    api_key: str | None = None
    model_name: str = Field(..., min_length=1)
    dimensions: int | None = None


class ConnectionTestResult(BaseModel):
    success: bool
    message: str
    latency_ms: int | None = None


class Job(BaseModel):
    """job record from database"""

    id: int
    pipeline_id: int
    status: str
    total_seeds: int
    current_seed: int = 0
    records_generated: int = 0
    records_failed: int = 0
    progress: float = 0.0
    current_block: str | None = None
    current_step: str | None = None
    error: str | None = None
    started_at: str
    completed_at: str | None = None
    created_at: str | None = None
    usage: dict[str, Any] | None = None


class PipelineRecord(BaseModel):
    """pipeline record from database"""

    id: int
    name: str
    definition: dict[str, Any]
    created_at: str
    validation_config: dict[str, Any] | None = None
