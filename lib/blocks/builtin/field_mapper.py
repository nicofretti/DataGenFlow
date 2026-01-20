import json
import logging
from typing import Any

from lib.blocks.base import BaseBlock
from lib.entities.block_execution_context import BlockExecutionContext
from lib.errors import BlockExecutionError
from lib.template_renderer import render_template

logger = logging.getLogger(__name__)


class FieldMapper(BaseBlock):
    """create new fields by rendering Jinja2 expressions"""

    name = "Field Mapper"
    description = "Create new fields by rendering Jinja2 expressions"
    category = "utilities"
    inputs = ["*"]
    outputs = ["*"]  # dynamic - frontend extracts keys from mappings config

    _config_descriptions = {
        "mappings": (
            "JSON object or Jinja template mapping field names to Jinja2 expressions. "
            'Example: {"question": "{{ parsed_json.qa.q }}"} or {{ mappings | tojson }}'
        )
    }

    _config_formats = {
        "mappings": "json-or-template",
    }

    def __init__(self, mappings: str | dict[str, str] = "{}"):
        """
        Args:
            mappings: JSON object or template of {"field_name": "{{ jinja2.expression }}"}
        """
        # handle both string (from UI/templates with jinja) and dict (from static YAML)
        if isinstance(mappings, dict):
            self.mappings_template = json.dumps(mappings) if mappings else "{}"
        else:
            self.mappings_template = mappings

    async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
        # parse mappings from template
        if not self.mappings_template or self.mappings_template == "{}":
            logger.warning("no mappings configured, returning empty result")
            return {}

        mappings_rendered = render_template(self.mappings_template, context.accumulated_state)
        try:
            mappings = json.loads(mappings_rendered)
            if not isinstance(mappings, dict):
                raise BlockExecutionError(
                    "mappings must be a JSON object",
                    detail={"rendered_value": mappings_rendered},
                )
            # validate all values are strings (Jinja2 templates)
            for key, value in mappings.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    raise BlockExecutionError(
                        "All mappings keys and values must be strings",
                        detail={"mappings": mappings},
                    )
        except json.JSONDecodeError as e:
            raise BlockExecutionError(
                f"mappings must be valid JSON: {str(e)}",
                detail={
                    "template": self.mappings_template,
                    "rendered": mappings_rendered,
                },
            )

        result = {}
        for field_name, template in mappings.items():
            try:
                rendered = render_template(template, context.accumulated_state)
                result[field_name] = self._maybe_parse_json(rendered)
            except Exception as e:
                logger.error(f"failed to render template for '{field_name}': {e}")
                result[field_name] = ""

        return result

    def _maybe_parse_json(self, value: str) -> Any:
        """parse JSON if possible, otherwise return string"""
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
