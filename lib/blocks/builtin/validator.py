import json
from typing import Any

from lib.blocks.base import BaseBlock
from lib.entities.block_execution_context import BlockExecutionContext
from lib.errors import BlockExecutionError
from lib.template_renderer import render_template


class ValidatorBlock(BaseBlock):
    name = "Validator"
    description = "Validate text against rules"
    category = "validators"
    inputs = ["text", "assistant"]
    outputs = ["text", "valid", "assistant"]

    _config_descriptions = {
        "forbidden_words": (
            'JSON array or Jinja template. Examples: ["spam", "bad"] or '
            "{{ forbidden_words | tojson }} (leave empty for none)"
        )
    }

    _config_formats = {
        "forbidden_words": "json-or-template",
    }

    def __init__(
        self,
        min_length: int = 0,
        max_length: int = 100000,
        forbidden_words: str | list[str] = "",
    ) -> None:
        self.min_length = min_length
        self.max_length = max_length
        # handle both string (from UI/templates with jinja) and list (from static YAML)
        if isinstance(forbidden_words, list):
            self.forbidden_words_template = json.dumps(forbidden_words)
        else:
            self.forbidden_words_template = forbidden_words if forbidden_words else ""

    async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
        # parse forbidden_words from template (optional)
        forbidden_words: list[str] = []
        if self.forbidden_words_template:
            words_rendered = render_template(
                self.forbidden_words_template, context.accumulated_state
            )
            try:
                words_list = json.loads(words_rendered)
                if not isinstance(words_list, list):
                    raise BlockExecutionError(
                        "forbidden_words must be a JSON array",
                        detail={"rendered_value": words_rendered},
                    )
                if not all(isinstance(w, str) for w in words_list):
                    raise BlockExecutionError(
                        "All items in forbidden_words must be strings",
                        detail={"forbidden_words": words_list},
                    )
                forbidden_words = words_list
            except json.JSONDecodeError as e:
                raise BlockExecutionError(
                    f"forbidden_words must be valid JSON: {str(e)}",
                    detail={
                        "template": self.forbidden_words_template,
                        "rendered": words_rendered,
                    },
                )

        # validate either text or assistant field (prefer non-empty)
        text = context.get_state("text") or context.get_state("assistant", "")

        # check length
        if len(text) < self.min_length or len(text) > self.max_length:
            valid = False
        else:
            # check forbidden words
            text_lower = text.lower()
            valid = True
            for word in forbidden_words:
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
