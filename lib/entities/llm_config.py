from enum import Enum
from pydantic import BaseModel, Field

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

class EmbeddingModelConfig(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    provider: LLMProvider
    endpoint: str = ""
    api_key: str = ""
    model_name: str = Field(..., min_length=1)
    dimensions: int = 0

class ConnectionTestResult(BaseModel):
    success: bool
    message: str
    latency_ms: int = -1
