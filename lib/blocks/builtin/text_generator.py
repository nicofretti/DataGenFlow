import logging
from typing import Any

import litellm
from jinja2 import Environment, meta

from lib.blocks.base import BaseBlock
from lib.entities import pipeline
from lib.entities.block_execution_context import BlockExecutionContext
from lib.template_renderer import render_template

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

    def _prepare_prompts(self, data: dict[str, Any]) -> tuple[str, str]:
        """render jinja2 templates with data context"""
        system_template = self.system_prompt or data.get("system", "")
        user_template = self.user_prompt or data.get("user", "")

        system = render_template(system_template, data) if system_template else ""
        user = render_template(user_template, data) if user_template else ""

        return system, user

    def _build_messages(self, system: str, user: str) -> list[dict[str, str]]:
        """build messages array from prompts"""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        if user:
            messages.append({"role": "user", "content": user})
        return messages

    async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
        from app import llm_config_manager

        system, user = self._prepare_prompts(context.accumulated_state)
        messages = self._build_messages(system, user)

        llm_config = await llm_config_manager.get_llm_model(self.model_name)
        llm_params = llm_config_manager.prepare_llm_call(
            llm_config,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        # add langfuse trace grouping (trace_id always present in context)
        llm_params["metadata"] = {
            "trace_id": context.trace_id,
            "tags": ["datagenflow"],
        }

        logger.info(f"Calling LiteLLM with model={llm_params.get('model')}")

        try:
            response = await litellm.acompletion(**llm_params)
        except Exception as e:
            logger.error(f"LLM call failed for {self.name}: {e}")
            raise

        assistant = response.choices[0].message.content

        # extract usage info from response
        usage_info = pipeline.Usage(
            input_tokens=response.usage.prompt_tokens or 0,
            output_tokens=response.usage.completion_tokens or 0,
            cached_tokens=getattr(response.usage, "cache_read_input_tokens", 0) or 0,
        )

        return {
            "assistant": assistant,
            "system": system,
            "user": user,
            "_usage": usage_info.model_dump(),
        }

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
