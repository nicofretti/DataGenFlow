from typing import Any

from lib.blocks.base import BaseBlock
from lib.generator import Generator
from models import GenerationConfig


class LLMBlock(BaseBlock):
    name = "LLM Generator"
    description = "Generate text using LLM"
    inputs = ["system", "user"]
    outputs = ["assistant"]

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

        system = data.get("system", "")
        user = data.get("user", "")

        assistant = await generator.generate(system, user)

        return {"assistant": assistant}
