import json
import logging
from typing import TYPE_CHECKING, Any

import litellm
from jinja2 import Environment, meta

from lib.blocks.base import BaseBlock
from lib.template_renderer import render_template

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class StructuredGenerator(BaseBlock):
    name = "Structured Generator"
    description = "Generate structured JSON data using LLM with schema validation"
    category = "generators"
    inputs = []
    outputs = ["generated"]

    _config_descriptions = {
        "model": "Select LLM model to use (leave empty for default)",
        "user_prompt": (
            "Jinja2 template. Reference fields with {{ field_name }} or "
            "{{ metadata.field_name }}. Example: Generate data for {{ metadata.topic }}"
        ),
        "json_schema": "JSON Schema defining the structure of generated data",
    }

    def __init__(
        self,
        json_schema: dict[str, Any],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        user_prompt: str = "",
    ):
        self.json_schema = json_schema
        self.model_name = model  # model name or None for default
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.user_prompt = user_prompt

    async def execute(self, data: dict[str, Any]) -> dict[str, Any]:
        # late import to avoid circular dependency
        from app import llm_config_manager

        # use config user_prompt or data user_prompt
        prompt_template = self.user_prompt or data.get(
            "user_prompt", "Generate data according to schema"
        )

        # render the Jinja2 template with data context
        user_prompt = render_template(prompt_template, data)

        messages = [{"role": "user", "content": user_prompt}]

        # prepare response_format with schema enforcement
        response_format: dict[str, Any]
        if self.json_schema:
            response_format = {
                "type": "json_schema",
                "json_schema": {"name": "response", "schema": self.json_schema, "strict": True},
            }
        else:
            # fallback to basic json mode
            response_format = {"type": "json_object"}

        # get llm config and prepare call
        llm_config = await llm_config_manager.get_llm_model(self.model_name)
        llm_params = llm_config_manager.prepare_llm_call(
            llm_config,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_format=response_format,
        )

        logger.info(f"Calling LiteLLM with model={llm_params.get('model')}")

        try:
            response = await litellm.acompletion(**llm_params)
        except Exception as e:
            # fallback to basic json_object if structured outputs not supported
            logger.warning(f"Schema enforcement failed, falling back to json_object: {e}")
            llm_params["response_format"] = {"type": "json_object"}
            response = await litellm.acompletion(**llm_params)

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

    @classmethod
    def get_required_fields(cls, config: dict[str, Any]) -> list[str]:
        """extract required fields from jinja2 template in user_prompt"""
        env = Environment()
        user_prompt = config.get("user_prompt", "")

        if not user_prompt:
            return []

        try:
            ast = env.parse(user_prompt)
            variables = meta.find_undeclared_variables(ast)
            return sorted(list(variables))
        except Exception:
            return []
