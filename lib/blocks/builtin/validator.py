from typing import Any

from lib.blocks.base import BaseBlock
from lib.entities.block_execution_context import BlockExecutionContext


class ValidatorBlock(BaseBlock):
    name = "Validator"
    description = "Validate text against rules"
    category = "validators"
    inputs = ["text", "assistant"]
    outputs = ["text", "valid", "assistant"]

    _config_descriptions = {"forbidden_words": "List of words that should not appear in the text"}

    def __init__(
        self,
        min_length: int = 0,
        max_length: int = 100000,
        forbidden_words: list[str] | None = None,
    ) -> None:
        self.min_length = min_length
        self.max_length = max_length
        self.forbidden_words = forbidden_words or []

    async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
        # validate either text or assistant field (prefer non-empty)
        text = context.get_state("text") or context.get_state("assistant", "")

        # check length
        if len(text) < self.min_length or len(text) > self.max_length:
            valid = False
        else:
            # check forbidden words
            text_lower = text.lower()
            valid = True
            for word in self.forbidden_words:
                if word.lower() in text_lower:
                    valid = False
                    break

        # return only declared outputs
        result = {"valid": valid}
        if "text" in context.accumulated_state:
            result["text"] = context.accumulated_state["text"]
        if "assistant" in context.accumulated_state:
            result["assistant"] = context.accumulated_state["assistant"]

        return result
