import inspect
from abc import ABC, abstractmethod
from typing import Any


class BaseBlock(ABC):
    name: str = "Base Block"
    description: str = "Base block description"
    inputs: list[str] = []
    outputs: list[str] = []

    @abstractmethod
    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        pass

    @classmethod
    def get_schema(cls) -> dict[str, Any]:
        # introspect __init__ to extract config parameters
        sig = inspect.signature(cls.__init__)
        config_schema = {}

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            param_type = "string"
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int:
                    param_type = "number"
                elif param.annotation == float:
                    param_type = "number"
                elif param.annotation == bool:
                    param_type = "boolean"

            config_schema[param_name] = {
                "type": param_type,
                "required": param.default == inspect.Parameter.empty,
                "default": None if param.default == inspect.Parameter.empty else param.default,
            }

        return {
            "type": cls.__name__,
            "name": cls.name,
            "description": cls.description,
            "inputs": cls.inputs,
            "outputs": cls.outputs,
            "config_schema": config_schema,
        }
