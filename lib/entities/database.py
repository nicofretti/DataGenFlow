from typing import Any
from pydantic import BaseModel, field_validator

class PipelineRecord(BaseModel):
    """pipeline record from database"""
    id: int
    name: str
    definition: dict[str, Any]
    created_at: str
    validation_config: dict[str, Any] = {}

    @field_validator("validation_config", mode="before")
    @classmethod
    def validate_config(cls, v: dict[str, Any] | None) -> dict[str, Any]:
        """convert None to empty dict for database compatibility"""
        return v if v is not None else {}
