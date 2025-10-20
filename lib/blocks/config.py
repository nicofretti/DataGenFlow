import inspect
from typing import get_type_hints, Any


class BlockConfigSchema:
    @staticmethod
    def get_config_schema(block_class) -> dict:
        """extract config schema from __init__ signature"""
        sig = inspect.signature(block_class.__init__)
        type_hints = get_type_hints(block_class.__init__)

        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            param_type = type_hints.get(param_name, str)
            property_def = BlockConfigSchema._get_property_def(param_type)

            if param.default != inspect.Parameter.empty:
                property_def["default"] = param.default
            else:
                required.append(param_name)

            properties[param_name] = property_def

        return {
            "type": "object",
            "properties": properties,
            "required": required
        }

    @staticmethod
    def _get_property_def(param_type) -> dict:
        """convert Python type to JSON schema"""
        if param_type == int:
            return {"type": "integer"}
        elif param_type == float:
            return {"type": "number"}
        elif param_type == bool:
            return {"type": "boolean"}
        elif param_type == str:
            return {"type": "string"}
        else:
            return {"type": "string"}
