import re
from abc import ABC, abstractmethod
from typing import Any

from lib.blocks.config import BlockConfigSchema


class BaseBlock(ABC):
    name: str = "Base Block"
    description: str = "Base block description"
    inputs: list[str] = []
    outputs: list[str] = []

    @abstractmethod
    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
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
            "inputs": cls.inputs,
            "outputs": cls.outputs,
            "config_schema": cls.get_config_schema(),
        }

    @staticmethod
    def extract_template_vars(text: str) -> list[str]:
        """extract {variable} placeholders from text"""
        return list(set(re.findall(r"\{(\w+)\}", text)))
