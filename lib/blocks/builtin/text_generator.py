from lib.blocks.base import BaseBlock
import litellm
from typing import Any
from config import settings
import logging

logger = logging.getLogger(__name__)


class TextGenerator(BaseBlock):
    name = "Text Generator"
    description = "Generate text using LLM with configurable parameters"
    inputs = []
    outputs = ["assistant", "system", "user"]

    _config_descriptions = {
        "system_prompt": "Jinja2 template. Reference fields with {{ field_name }} or {{ metadata.field_name }}",
        "user_prompt": "Jinja2 template. Reference fields with {{ field_name }} or {{ metadata.field_name }}"
    }

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

        # add ollama/ prefix if using ollama endpoint and model doesn't have provider prefix
        model = self.model

        # for ollama, litellm expects just the model with ollama/ prefix
        if "11434" in settings.LLM_ENDPOINT and "/" not in model:
            model = f"ollama/{model}"
            # extract base url from endpoint (remove /v1/chat/completions or /api/generate)
            import re
            api_base = re.sub(r'/(v1/chat/completions|api/generate).*$', '', settings.LLM_ENDPOINT)
            logger.info(f"Calling LiteLLM ollama with model={model}, api_base={api_base}")
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                api_base=api_base
            )
        else:
            # for other providers, use api_base
            logger.info(f"Calling LiteLLM with model={model}, api_base={settings.LLM_ENDPOINT}")
            response = await litellm.acompletion(
                model=model,
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
