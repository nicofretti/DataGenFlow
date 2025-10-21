import inspect
from typing import get_type_hints, get_origin, get_args, Any, Union


class BlockConfigSchema:
    @staticmethod
    def get_config_schema(block_class) -> dict:
        """extract config schema from __init__ signature"""
        sig = inspect.signature(block_class.__init__)
        type_hints = get_type_hints(block_class.__init__)

        # check for class-level enum and field reference definitions
        enum_values = getattr(block_class, '_config_enums', {})
        field_refs = getattr(block_class, '_field_references', [])

        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            param_type = type_hints.get(param_name, str)
            property_def = BlockConfigSchema._get_property_def(param_type)

            # add default value if present
            if param.default != inspect.Parameter.empty:
                property_def["default"] = param.default
            else:
                required.append(param_name)

            # add enum values if defined
            if param_name in enum_values:
                property_def["enum"] = enum_values[param_name]

            # mark as field reference for UI dropdown
            if param_name in field_refs:
                property_def["isFieldReference"] = True

            properties[param_name] = property_def

        return {
            "type": "object",
            "properties": properties,
            "required": required
        }

    @staticmethod
    def _get_property_def(param_type) -> dict:
        """convert Python type to JSON schema"""
        # handle union types (e.g., str | None, list[str] | None)
        origin = get_origin(param_type)
        if origin is Union:
            args = get_args(param_type)
            # filter out NoneType from union
            non_none_types = [arg for arg in args if arg is not type(None)]
            if len(non_none_types) == 1:
                # if only one non-None type, use that type
                return BlockConfigSchema._get_property_def(non_none_types[0])
            # if multiple non-None types, use the first one
            if non_none_types:
                return BlockConfigSchema._get_property_def(non_none_types[0])

        # handle list types
        if origin is list:
            args = get_args(param_type)
            item_type = args[0] if args else str
            return {
                "type": "array",
                "items": BlockConfigSchema._get_property_def(item_type)
            }

        # handle basic types
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
