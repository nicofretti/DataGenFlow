from typing import Any
from pydantic import BaseModel, Field

class GenerationConfig(BaseModel):
    model: str = ""
    endpoint: str = ""
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1000, ge=1)

class SeedValidationRequest(BaseModel):
    pipeline_id: int
    seeds: list[dict[str, Any]]
