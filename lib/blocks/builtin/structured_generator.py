import json
import logging
from typing import Any

import litellm

from config import settings
from lib.blocks.base import BaseBlock
from lib.template_renderer import render_template

logger = logging.getLogger(__name__)


class StructuredGenerator(BaseBlock):
    name = "Structured Generator"
    description = "Generate structured JSON data using LLM with schema validation"
    inputs = []
    outputs = ["generated"]

    _config_descriptions = {
        "prompt": "Jinja2 template. Reference fields with {{ field_name }} or {{ metadata.field_name }}. Example: Generate data for {{ metadata.topic }}",
        "json_schema": "JSON Schema defining the structure of generated data",
    }

    def __init__(
        self,
        json_schema: dict[str, Any],
        model: str | None = settings.LLM_MODEL,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        prompt: str = "prompt",
    ):
        self.json_schema = json_schema
        self.model = model or settings.LLM_MODEL
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.prompt = prompt

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        # use config prompt or data prompt
        prompt_template = self.prompt or data.get(
            "prompt", "Generate data according to schema"
        )

        # render the Jinja2 template with data context
        user_prompt = render_template(prompt_template, data)

        messages = [{"role": "user", "content": user_prompt}]

        # add ollama/ prefix if using ollama endpoint and model doesn't have provider prefix
        model = self.model

        # prepare response_format with schema enforcement
        response_format: dict[str, Any]
        if self.json_schema:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "response",
                    "schema": self.json_schema,
                    "strict": True
                }
            }
        else:
            # fallback to basic json mode
            response_format = {"type": "json_object"}

        # for ollama, litellm expects just the model with ollama/ prefix
        if "11434" in settings.LLM_ENDPOINT and "/" not in model:
            model = f"ollama/{model}"
            # extract base url from endpoint (remove /v1/chat/completions or /api/generate)
            import re

            api_base = re.sub(
                r"/(v1/chat/completions|api/generate).*$", "", settings.LLM_ENDPOINT
            )
            logger.info(
                f"Calling LiteLLM ollama with model={model}, api_base={api_base}"
            )

            try:
                response = await litellm.acompletion(
                    model=model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    response_format=response_format,
                    api_base=api_base,
                )
            except Exception as e:
                # fallback to basic json_object if structured outputs not supported
                logger.warning(f"Schema enforcement failed, falling back to json_object: {e}")
                response = await litellm.acompletion(
                    model=model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    response_format={"type": "json_object"},
                    api_base=api_base,
                )
        else:
            # for other providers, use api_base
            logger.info(
                f"Calling LiteLLM with model={model}, api_base={settings.LLM_ENDPOINT}"
            )

            try:
                response = await litellm.acompletion(
                    model=model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    response_format=response_format,
                    api_key=settings.LLM_API_KEY,
                    api_base=settings.LLM_ENDPOINT,
                )
            except Exception as e:
                # fallback to basic json_object if structured outputs not supported
                logger.warning(f"Schema enforcement failed, falling back to json_object: {e}")
                response = await litellm.acompletion(
                    model=model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    response_format={"type": "json_object"},
                    api_key=settings.LLM_API_KEY,
                    api_base=settings.LLM_ENDPOINT,
                )

        content = response.choices[0].message.content

        # parse JSON response
        try:
            generated = json.loads(content)
        except json.JSONDecodeError:
            # fallback: extract JSON from markdown code blocks
            import re

            json_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", content, re.DOTALL)
            if json_match:
                generated = json.loads(json_match.group(1))
            else:
                generated = {"raw_response": content}

        return {"generated": generated}
