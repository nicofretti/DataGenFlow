import json
import logging
import re
from typing import Any, ClassVar

import litellm
from jinja2 import Environment, meta

from lib.blocks.base import BaseBlock
from lib.entities import pipeline
from lib.entities.block_execution_context import BlockExecutionContext
from lib.errors import BlockExecutionError
from lib.template_renderer import render_template

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
        "json_schema": (
            'JSON object or Jinja template. Example: {"type": "object", "properties": {...}} or '
            "{{ json_schema | tojson }}"
        ),
    }

    _config_formats: ClassVar[dict[str, str]] = {
        "json_schema": "json-or-template",
    }

    def __init__(
        self,
        json_schema: str | dict[str, Any],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        user_prompt: str = "",
    ):
        # handle both string (from UI/templates with jinja) and dict (from static YAML)
        if isinstance(json_schema, dict):
            self.json_schema_template = json.dumps(json_schema)
        else:
            self.json_schema_template = json_schema
        self.model_name = model  # model name or None for default
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.user_prompt = user_prompt

    def _prepare_prompt(self, data: dict[str, Any]) -> str:
        """render jinja2 template with data context"""
        prompt_template = self.user_prompt or data.get(
            "user_prompt", "Generate data according to schema"
        )
        return render_template(prompt_template, data)

    def _prepare_response_format(self, json_schema: dict[str, Any]) -> dict[str, Any]:
        """prepare response format with schema enforcement"""
        if json_schema:
            return {
                "type": "json_schema",
                "json_schema": {
                    "name": "response",
                    "schema": json_schema,
                    "strict": True,
                },
            }
        return {"type": "json_object"}

    async def _call_llm_with_fallback(self, llm_params: dict[str, Any]) -> Any:
        """call llm with fallback to basic json_object on schema errors"""
        logger.info(f"Calling LiteLLM with model={llm_params.get('model')}")
        try:
            return await litellm.acompletion(**llm_params)
        except Exception as e:
            logger.warning(f"Schema enforcement failed, falling back to json_object: {e}")
            llm_params["response_format"] = {"type": "json_object"}
            return await litellm.acompletion(**llm_params)

    def _parse_json_response(self, content: str) -> dict[str, Any]:
        """parse json from llm response with fallback for code blocks"""
        try:
            result = json.loads(content)
            return result if isinstance(result, dict) else {"raw_response": content}
        except json.JSONDecodeError:
            json_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
                return result if isinstance(result, dict) else {"raw_response": content}
            return {"raw_response": content}

    async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
        from app import llm_config_manager

        # parse json_schema from template
        schema_rendered = render_template(self.json_schema_template, context.accumulated_state)
        try:
            json_schema = json.loads(schema_rendered)
            if not isinstance(json_schema, dict):
                raise BlockExecutionError(
                    "json_schema must be a JSON object",
                    detail={"rendered_value": schema_rendered},
                )
        except json.JSONDecodeError as e:
            raise BlockExecutionError(
                f"json_schema must be valid JSON: {e!s}",
                detail={
                    "template": self.json_schema_template,
                    "rendered": schema_rendered,
                },
            ) from e

        user_prompt = self._prepare_prompt(context.accumulated_state)
        messages = [{"role": "user", "content": user_prompt}]
        response_format = self._prepare_response_format(json_schema)

        llm_config = await llm_config_manager.get_llm_model(self.model_name)
        llm_params = llm_config_manager.prepare_llm_call(
            llm_config,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_format=response_format,
        )

        # add langfuse trace grouping (trace_id always present in context)
        llm_params["metadata"] = {
            "trace_id": context.trace_id,
            "tags": ["datagenflow"],
        }

        response = await self._call_llm_with_fallback(llm_params)
        content = response.choices[0].message.content
        generated = self._parse_json_response(content)

        # extract usage info from response
        usage_info = pipeline.Usage(
            input_tokens=response.usage.prompt_tokens or 0,
            output_tokens=response.usage.completion_tokens or 0,
            cached_tokens=getattr(response.usage, "cache_read_input_tokens", 0) or 0,
        )

        return {"generated": generated, "_usage": usage_info.model_dump()}

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
        except Exception as e:
            logger.warning(f"Failed to parse Jinja2 template for required fields: {e}")
            return []
