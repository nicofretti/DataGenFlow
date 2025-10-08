from typing import Any

from lib.blocks.base import BaseBlock
from lib.generator import Generator
from lib.template_renderer import render_template
from models import GenerationConfig


class LLMBlock(BaseBlock):
    name = "LLM Generator"
    description = "Generate text using LLM with Jinja2 template rendering"
    inputs = ["system", "user"]
    outputs = ["assistant", "system", "user"]

    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        config = GenerationConfig(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        generator = Generator(config)

        # render system and user templates with accumulated data
        system_template = data.get("system", "")
        user_template = data.get("user", "")

        system = render_template(system_template, data) if system_template else ""
        user = render_template(user_template, data) if user_template else ""

        assistant = await generator.generate(system, user)

        # return rendered prompts and assistant response
        return {"assistant": assistant, "system": system, "user": user}
