from lib.blocks.base import BaseBlock
import litellm
import json
from typing import Any
from config import settings


class StructuredGenerator(BaseBlock):
    name = "Structured Generator"
    description = "Generate structured JSON data using LLM with schema validation"
    inputs = []
    outputs = ["generated"]

    def __init__(
        self,
        json_schema: dict[str, Any],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        prompt: str = ""
    ):
        self.json_schema = json_schema
        self.model = model or settings.LLM_MODEL
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.prompt = prompt

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        # use config prompt or data prompt
        user_prompt = self.prompt or data.get("prompt", "Generate data according to schema")

        messages = [{"role": "user", "content": user_prompt}]

        # use litellm with response_format for structured output
        response = await litellm.acompletion(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_format={"type": "json_object"},
            api_key=settings.LLM_API_KEY,
            api_base=settings.LLM_ENDPOINT
        )

        content = response.choices[0].message.content

        # parse JSON response
        try:
            generated = json.loads(content)
        except json.JSONDecodeError:
            # fallback: extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', content, re.DOTALL)
            if json_match:
                generated = json.loads(json_match.group(1))
            else:
                generated = {"raw_response": content}

        return {"generated": generated}
