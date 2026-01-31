from typing import Any

from pydantic import BaseModel


class BlockInfo(BaseModel):
    """block schema with extensibility metadata"""

    type: str
    name: str
    description: str
    category: str
    inputs: list[str]
    outputs: list[str]
    config_schema: dict[str, Any]
    is_multiplier: bool = False
    dependencies: list[str] = []
    source: str = "builtin"
    available: bool = True
    error: str | None = None


class TemplateInfo(BaseModel):
    """template listing with source metadata"""

    id: str
    name: str
    description: str
    example_seed: list[dict[str, Any]] | None = None
    source: str = "builtin"


class BlocksStatus(BaseModel):
    total: int
    builtin_blocks: int
    custom_blocks: int
    user_blocks: int
    available: int
    unavailable: int


class TemplatesStatus(BaseModel):
    total: int
    builtin_templates: int
    user_templates: int


class ExtensionsStatus(BaseModel):
    blocks: BlocksStatus
    templates: TemplatesStatus


class DependencyInfo(BaseModel):
    requirement: str
    name: str
    installed_version: str | None = None
    status: str  # "ok", "not_installed", "invalid"
    error: str | None = None
