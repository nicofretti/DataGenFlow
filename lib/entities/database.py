from typing import Any

from pydantic import BaseModel, Field, field_validator

from lib.entities.pipeline import FieldOrder, ValidationConfig


class PipelineRecord(BaseModel):
    """pipeline record from database"""

    id: int
    name: str
    definition: dict[str, Any]
    created_at: str
    validation_config: ValidationConfig = Field(
        default_factory=lambda: ValidationConfig(field_order=FieldOrder())
    )

    @field_validator("validation_config", mode="before")
    @classmethod
    def validate_config(cls, v: ValidationConfig | dict[str, Any] | None) -> ValidationConfig:
        """convert from dict/None to ValidationConfig"""
        if v is None or v == {}:
            return ValidationConfig(field_order=FieldOrder())
        if isinstance(v, ValidationConfig):
            return v
        if isinstance(v, dict):
            return ValidationConfig(**v)
        return ValidationConfig(field_order=FieldOrder())
