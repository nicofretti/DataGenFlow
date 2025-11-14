import logging
from typing import TYPE_CHECKING, Any

import litellm
from jinja2 import Environment, meta

from lib.blocks.base import BaseBlock
from lib.template_renderer import render_template

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class TextGenerator(BaseBlock):
    name = "Text Generator"
    description = "Generate text using LLM with configurable parameters"
    category = "generators"
    inputs = []
    outputs = ["assistant", "system", "user"]

    _config_descriptions = {
        "model": "Select LLM model to use (leave empty for default)",
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
        self.model_name = model  # model name or None for default
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        # late import to avoid circular dependency
        from app import llm_config_manager

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

        # get llm config and prepare call
        llm_config = await llm_config_manager.get_llm_model(self.model_name)
        llm_params = llm_config_manager.prepare_llm_call(
            llm_config, messages=messages, temperature=self.temperature, max_tokens=self.max_tokens
        )

        logger.info(f"Calling LiteLLM with model={llm_params.get('model')}")

        # call litellm with prepared config
        response = await litellm.acompletion(**llm_params)

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
