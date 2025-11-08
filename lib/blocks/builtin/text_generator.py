import logging
from typing import Any

import litellm
from jinja2 import Environment, meta

from config import settings
from lib.blocks.base import BaseBlock
from lib.template_renderer import render_template

logger = logging.getLogger(__name__)


class TextGenerator(BaseBlock):
    name = "Text Generator"
    description = "Generate text using LLM with configurable parameters"
    category = "generators"
    inputs = []
    outputs = ["assistant", "system", "user"]

    _config_descriptions = {
        "system_prompt": (
            "Jinja2 template. Reference fields with {{ field_name }} or {{ metadata.field_name }}"
        ),
        "user_prompt": (
            "Jinja2 template. Reference fields with {{ field_name }} or {{ metadata.field_name }}"
        ),
    }

    def __init__(
        self,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        system_prompt: str = "",
        user_prompt: str = "",
    ):
        self.model = model or settings.LLM_MODEL
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt

    def _prepare_llm_config(self) -> tuple[str, str, str | None]:
        """returns (model, api_base, api_key) for litellm"""
        is_ollama = "11434" in settings.LLM_ENDPOINT

        if is_ollama:
            # add ollama/ prefix if not already present
            model = f"ollama/{self.model}" if "/" not in self.model else self.model
            # extract base url (remove /v1/chat/completions or /api/generate)
            import re

            api_base = re.sub(r"/(v1/chat/completions|api/generate).*$", "", settings.LLM_ENDPOINT)
            api_key = None
        else:
            model = self.model
            api_base = settings.LLM_ENDPOINT
            api_key = settings.LLM_API_KEY

        return model, api_base, api_key

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        # use config prompts or data prompts
        system_template = self.system_prompt or data.get("system", "")
        user_template = self.user_prompt or data.get("user", "")

        # render Jinja2 templates with data context
        system = render_template(system_template, data) if system_template else ""
        user = render_template(user_template, data) if user_template else ""

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if user:
            messages.append({"role": "user", "content": user})

        # prepare llm configuration
        model, api_base, api_key = self._prepare_llm_config()

        logger.info(f"Calling LiteLLM with model={model}, api_base={api_base}")

        # call litellm with prepared config
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            api_base=api_base,
            api_key=api_key,
        )

        assistant = response.choices[0].message.content

        return {"assistant": assistant, "system": system, "user": user}

    @classmethod
    def get_required_fields(cls, config: dict[str, Any]) -> list[str]:
        """extract required fields from jinja2 templates in prompts"""
        env = Environment()
        required = set()

        system_prompt = config.get("system_prompt", "")
        user_prompt = config.get("user_prompt", "")

        for prompt in [system_prompt, user_prompt]:
            if prompt:
                try:
                    ast = env.parse(prompt)
                    variables = meta.find_undeclared_variables(ast)
                    required.update(variables)
                except Exception as e:
                    logger.warning(
                        f"Failed to parse Jinja2 template for required fields: {e} "
                        f"(prompt: {prompt!r})"
                    )

        return sorted(list(required))
