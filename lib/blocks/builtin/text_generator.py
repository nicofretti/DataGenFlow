from lib.blocks.base import BaseBlock
import litellm
from typing import Any
from config import settings


class TextGenerator(BaseBlock):
    name = "Text Generator"
    description = "Generate text using LLM with configurable parameters"
    inputs = []
    outputs = ["assistant", "system", "user"]

    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        system_prompt: str = "",
        user_prompt: str = ""
    ):
        self.model = model or settings.LLM_MODEL
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        # use config prompts or data prompts
        system = self.system_prompt or data.get("system", "")
        user = self.user_prompt or data.get("user", "")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if user:
            messages.append({"role": "user", "content": user})

        response = await litellm.acompletion(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            api_key=settings.LLM_API_KEY,
            api_base=settings.LLM_ENDPOINT
        )

        assistant = response.choices[0].message.content

        return {
            "assistant": assistant,
            "system": system,
            "user": user
        }
