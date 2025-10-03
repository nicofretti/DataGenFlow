from typing import Any

from lib.blocks.base import BaseBlock


class ValidatorBlock(BaseBlock):
    name = "Validator"
    description = "Validate text against rules"
    inputs = ["text"]
    outputs = ["text", "valid"]

    def __init__(
        self,
        min_length: int = 0,
        max_length: int = 100000,
        forbidden_words: list[str] | None = None,
    ) -> None:
        self.min_length = min_length
        self.max_length = max_length
        self.forbidden_words = forbidden_words or []

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        text = data.get("text", "")

        # check length
        if len(text) < self.min_length or len(text) > self.max_length:
            return {"text": text, "valid": False}

        # check forbidden words
        text_lower = text.lower()
        for word in self.forbidden_words:
            if word.lower() in text_lower:
                return {"text": text, "valid": False}

        return {"text": text, "valid": True}
