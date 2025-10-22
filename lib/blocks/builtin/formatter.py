from typing import Any

from lib.blocks.base import BaseBlock
from lib.template_renderer import render_template


class OutputBlock(BaseBlock):
    name = "Pipeline Output"
    description = "Define final pipeline output using Jinja2 templates for the review system"
    inputs = ["*"]
    outputs = ["pipeline_output"]

    _config_descriptions = {
        "format_template": "Jinja2 template. Reference fields with {{ field_name }} or {{ metadata.field_name }}. Supports filters and conditionals."
    }

    def __init__(self, format_template: str = "Result: {{ assistant }}") -> None:
        self.format_template = format_template

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        format output using jinja2 template with full access to accumulated state

        examples:
        - "{{ assistant }}" - simple variable
        - "{% if user %}User: {{ user }}{% endif %}" - conditional
        - "{{ assistant | upper }}" - with filter
        - "{{ metadata.field }}" - nested access
        """
        formatted = render_template(self.format_template, data)
        return {"pipeline_output": formatted}
