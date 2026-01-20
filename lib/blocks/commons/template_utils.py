"""utility functions for template rendering and json parsing in blocks"""

import json
import logging
import re
from typing import Any, cast

from lib.errors import BlockExecutionError
from lib.template_renderer import render_template

logger = logging.getLogger(__name__)


def render_and_parse_json(
    template: str,
    context: dict[str, Any],
    field_name: str,
    expected_type: type,
) -> Any:
    """
    render jinja2 template and parse result as json
    validates the parsed value matches expected type (list or dict)
    """
    rendered = render_template(template, context)

    try:
        parsed = json.loads(rendered)
    except json.JSONDecodeError as e:
        raise BlockExecutionError(
            f"{field_name} must be valid JSON: {str(e)}",
            detail={
                "template": template,
                "rendered": rendered,
            },
        )

    if not isinstance(parsed, expected_type):
        type_name = expected_type.__name__
        raise BlockExecutionError(
            f"{field_name} must be a JSON {type_name}",
            detail={"rendered_value": rendered},
        )

    return parsed


def validate_string_list(value: list[Any], field_name: str) -> None:
    """validate that all items in list are strings"""
    if not all(isinstance(item, str) for item in value):
        raise BlockExecutionError(
            f"All items in {field_name} must be strings",
            detail={field_name: value},
        )


def normalize_template_param(value: Any, param_type: type) -> str:
    """
    convert list or dict to json string for template storage
    enables json-or-template pattern where param can be static json or jinja template
    """
    if isinstance(value, param_type):
        return json.dumps(value)
    return str(value)


def parse_llm_json_response(content: str, field_name: str) -> dict[str, Any]:
    """
    parse json from llm response with fallback strategies
    tries: direct parse, markdown code block extraction, regex json extraction
    """
    # strategy 1: direct parse
    try:
        return cast(dict[str, Any], json.loads(content))
    except json.JSONDecodeError:
        pass

    # strategy 2: extract from markdown code block
    markdown_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if markdown_match:
        try:
            return cast(dict[str, Any], json.loads(markdown_match.group(1)))
        except json.JSONDecodeError:
            pass

    # strategy 3: find first json object with regex
    json_match = re.search(r"\{.*\}", content, re.DOTALL)
    if json_match:
        try:
            return cast(dict[str, Any], json.loads(json_match.group(0)))
        except json.JSONDecodeError:
            pass

    raise BlockExecutionError(
        f"Failed to parse {field_name} as JSON from LLM response",
        detail={"content": content[:500]},
    )


def clean_internal_fields(state: dict[str, Any]) -> dict[str, Any]:
    """
    remove internal fields (_usage, _hints, etc) from state
    returns new dict without mutation
    """
    return {key: value for key, value in state.items() if not key.startswith("_")}


def clean_metadata_fields(state: dict[str, Any]) -> dict[str, Any]:
    """
    remove pipeline metadata fields from state
    returns new dict without mutation
    """
    metadata_fields = {
        "samples",
        "target_count",
        "categorical_fields",
        "numeric_fields",
        "dependencies",
        "comparison_fields",
        "similarity_threshold",
        "fields_to_generate",
    }
    return {key: value for key, value in state.items() if key not in metadata_fields}


def render_template_or_return_default(
    template: str | None,
    context: dict[str, Any],
    default: str,
) -> str:
    """render template if provided, otherwise return default value"""
    if not template:
        return default
    return render_template(template, context)
