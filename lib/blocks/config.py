import inspect
from typing import Any, Type, Union, get_args, get_origin, get_type_hints


class BlockConfigSchema:
    @staticmethod
    def _build_property(
        param_name: str,
        param: inspect.Parameter,
        param_type: Any,
        enum_values: dict[str, Any],
        field_refs: list[str],
        field_descriptions: dict[str, str],
    ) -> tuple[dict[str, Any], bool]:
        """build property definition for a single parameter"""
        property_def = BlockConfigSchema._get_property_def(param_type)

        is_required = param.default == inspect.Parameter.empty
        if not is_required:
            property_def["default"] = param.default

        if param_name in enum_values:
            # for array types, apply enum to items
            if property_def.get("type") == "array":
                if "items" not in property_def:
                    property_def["items"] = {}
                property_def["items"]["enum"] = enum_values[param_name]
            else:
                property_def["enum"] = enum_values[param_name]
        if param_name in field_refs:
            property_def["isFieldReference"] = True
        if param_name in field_descriptions:
            property_def["description"] = field_descriptions[param_name]

        return property_def, is_required

    @staticmethod
    def get_config_schema(block_class: Type[Any]) -> dict[str, Any]:
        """extract config schema from __init__ signature"""
        sig = inspect.signature(block_class.__init__)
        type_hints = get_type_hints(block_class.__init__)

        enum_values = getattr(block_class, "_config_enums", {})
        field_refs = getattr(block_class, "_field_references", [])
        field_descriptions = getattr(block_class, "_config_descriptions", {})

        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            param_type = type_hints.get(param_name, str)
            property_def, is_required = BlockConfigSchema._build_property(
                param_name, param, param_type, enum_values, field_refs, field_descriptions
            )

            properties[param_name] = property_def
            if is_required:
                required.append(param_name)

        return {"type": "object", "properties": properties, "required": required}

    @staticmethod
    def _handle_union_type(args: tuple[Any, ...]) -> dict[str, Any] | None:
        """handle union types by filtering out NoneType"""
        non_none_types = [arg for arg in args if arg is not type(None)]
        if len(non_none_types) == 1:
            return BlockConfigSchema._get_property_def(non_none_types[0])
        if non_none_types:
            return BlockConfigSchema._get_property_def(non_none_types[0])
        return None

    @staticmethod
    def _handle_list_type(args: tuple[Any, ...]) -> dict[str, Any]:
        """handle list types with item schema"""
        item_type = args[0] if args else str
        return {"type": "array", "items": BlockConfigSchema._get_property_def(item_type)}

    @staticmethod
    def _get_basic_type(param_type: Any) -> dict[str, Any]:
        """convert basic Python type to JSON schema type"""
        if param_type is int:
            return {"type": "integer"}
        elif param_type is float:
            return {"type": "number"}
        elif param_type is bool:
            return {"type": "boolean"}
        elif param_type is str:
            return {"type": "string"}
        elif param_type is dict:
            return {"type": "object"}
        return {"type": "string"}

    @staticmethod
    def _get_property_def(param_type: Any) -> dict[str, Any]:
        """convert Python type to JSON schema"""
        origin = get_origin(param_type)

        if origin is Union:
            result = BlockConfigSchema._handle_union_type(get_args(param_type))
            if result:
                return result

        if origin is dict:
            return {"type": "object"}

        if origin is list:
            return BlockConfigSchema._handle_list_type(get_args(param_type))

        return BlockConfigSchema._get_basic_type(param_type)
