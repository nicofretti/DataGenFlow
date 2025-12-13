from typing import Any
from pydantic import BaseModel

class PipelineRecord(BaseModel):
    """pipeline record from database"""
    id: int
    name: str
    definition: dict[str, Any]
    created_at: str
    validation_config: dict[str, Any] = {}
