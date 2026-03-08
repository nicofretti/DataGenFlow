from enum import Enum

from pydantic import BaseModel, Field, field_validator


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"


class LLMModelConfig(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    provider: LLMProvider
    endpoint: str = ""
    api_key: str = ""
    model_name: str = Field(..., min_length=1)
    is_default: bool = False

    @field_validator("endpoint", "api_key", mode="before")
    @classmethod
    def validate_str_fields(cls, v: str | None) -> str:
        """convert None to empty string for database compatibility"""
        return v if v is not None else ""


class EmbeddingModelConfig(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    provider: LLMProvider
    endpoint: str = ""
    api_key: str = ""
    model_name: str = Field(..., min_length=1)
    is_default: bool = False
    dimensions: int = 0

    @field_validator("endpoint", "api_key", mode="before")
    @classmethod
    def validate_str_fields(cls, v: str | None) -> str:
        """convert None to empty string for database compatibility"""
        return v if v is not None else ""

    @field_validator("dimensions", mode="before")
    @classmethod
    def validate_dimensions(cls, v: int | None) -> int:
        """coerce None to 0"""
        return v if v is not None else 0


class ConnectionTestResult(BaseModel):
    success: bool
    message: str
    latency_ms: int = -1
