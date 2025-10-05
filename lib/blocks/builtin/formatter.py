from typing import Any

from lib.blocks.base import BaseBlock


class FormatterBlock(BaseBlock):
    name = "Output Formatter"
    description = "Format pipeline output for display"
    inputs = ["assistant"]
    outputs = ["pipeline_output"]

    def __init__(self, format_template: str = "Result: {assistant}") -> None:
        self.format_template = format_template

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        # format output using template
        try:
            formatted = self.format_template.format(**data)
        except KeyError as e:
            # fallback if template key missing
            formatted = f"Formatting error: missing key {e}"

        return {"pipeline_output": formatted}
