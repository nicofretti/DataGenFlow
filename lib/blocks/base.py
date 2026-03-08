from abc import ABC, abstractmethod
from typing import Any

from lib.blocks.config import BlockConfigSchema
from lib.entities.block_execution_context import BlockExecutionContext


class BaseBlock(ABC):
    name: str = "Base Block"
    description: str = "Base block description"
    category: str = "general"
    inputs: list[str] = []
    outputs: list[str] = []
    dependencies: list[str] = []

    @abstractmethod
    async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
        pass

    @classmethod
    def get_config_schema(cls) -> dict[str, Any]:
        """returns JSON schema for block configuration parameters"""
        return BlockConfigSchema.get_config_schema(cls)

    @classmethod
    def get_required_fields(cls, config: dict[str, Any]) -> list[str]:
        """returns list of required fields for this block instance based on config"""
        if "*" in cls.inputs:
            return []
        return cls.inputs

    @classmethod
    def get_schema(cls) -> dict[str, Any]:
        """returns full block schema (inputs, outputs, config)"""
        return {
            "type": cls.__name__,
            "name": cls.name,
            "description": cls.description,
            "category": cls.category,
            "inputs": cls.inputs,
            "outputs": cls.outputs,
            "config_schema": cls.get_config_schema(),
            "is_multiplier": getattr(cls, "is_multiplier", False),
            "dependencies": cls.dependencies,
        }


class BaseMultiplierBlock(BaseBlock):
    """base class for blocks that generate multiple outputs from single input"""

    category: str = "seeders"
    is_multiplier: bool = True

    @abstractmethod
    async def execute(self, context: BlockExecutionContext) -> list[dict[str, Any]]:  # type: ignore[override]
        """multiplier blocks return list of dicts instead of single dict"""
        pass
