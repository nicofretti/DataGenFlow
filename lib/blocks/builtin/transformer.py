from typing import Any

from lib.blocks.base import BaseBlock


class TransformerBlock(BaseBlock):
    name = "Transformer"
    description = "Transform text using operations"
    inputs = ["text"]
    outputs = ["text"]

    def __init__(self, operation: str = "strip") -> None:
        self.operation = operation

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        text = data.get("text", "")

        if self.operation == "lowercase":
            text = text.lower()
        elif self.operation == "uppercase":
            text = text.upper()
        elif self.operation == "strip":
            text = text.strip()
        elif self.operation == "trim":
            # remove extra whitespace
            text = " ".join(text.split())

        return {"text": text}
