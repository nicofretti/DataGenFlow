import json
import logging
from typing import Any

from lib.blocks.base import BaseBlock
from lib.entities.block_execution_context import BlockExecutionContext
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
            "Dict mapping new field names to Jinja2 expressions. "
            'Example: {"question": "{{ parsed_json.qa.q }}"}'
        )
    }

    def __init__(self, mappings: dict[str, str] | None = None):
        """
        Args:
            mappings: {"field_name": "{{ jinja2.expression }}"}
        """
        self.mappings = mappings or {}

    async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
        if not self.mappings:
            logger.warning("no mappings configured, returning empty result")
            return {}

        result = {}
        for field_name, template in self.mappings.items():
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
