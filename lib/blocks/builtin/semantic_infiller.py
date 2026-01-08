import json
import logging
import re
from typing import Any

import litellm

from lib.blocks.base import BaseBlock
from lib.entities import pipeline
from lib.entities.block_execution_context import BlockExecutionContext
from lib.errors import BlockExecutionError

logger = logging.getLogger(__name__)


class SemanticInfiller(BaseBlock):
    name = "Semantic Infiller"
    description = "Complete skeleton records using LLM to generate free-text fields"
    category = "generators"
    inputs = ["*"]  # accepts any skeleton fields
    outputs = ["*"]  # returns merged skeleton + generated fields

    _config_descriptions = {
        "fields_to_generate": "List of field names for LLM to generate (e.g., ['bio', 'description'])",
        "model": "Select LLM model to use (leave empty for default)",
        "temperature": "Sampling temperature (0.0 = deterministic, 1.0 = creative)",
        "max_tokens": "Maximum tokens for generated response",
        "system_prompt": "Custom system prompt (optional, overrides default)",
    }

    def __init__(
        self,
        fields_to_generate: list[str],
        model: str | None = None,
        temperature: float = 0.8,
        max_tokens: int = 500,
        system_prompt: str = "",
    ):
        self.fields_to_generate = fields_to_generate
        self.model_name = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt

    def _build_generation_prompt(
        self, skeleton: dict[str, Any], hints: dict[str, Any]
    ) -> str:
        """
        construct LLM prompt with constraints and hints

        format:
        - specify fields to generate
        - lock categorical constraints from skeleton
        - provide numeric hints and exemplars
        """
        fields_str = ", ".join(f'"{field}"' for field in self.fields_to_generate)

        # extract constraints (non-hint fields)
        constraints = []
        for key, value in skeleton.items():
            constraints.append(f'  - {key}: "{value}" (FIXED)')

        constraints_str = "\n".join(constraints) if constraints else "  (none)"

        # extract hints
        hint_lines = []
        for key, value in hints.items():
            if key.endswith("_range") and isinstance(value, list) and len(value) == 2:
                field_name = key.replace("_range", "")
                hint_lines.append(f"  - {field_name} should be between {value[0]}-{value[1]}")
            elif key == "exemplars" and isinstance(value, list):
                hint_lines.append("  - Example records for reference:")
                for ex in value[:2]:  # show max 2 exemplars
                    # only show generated fields from exemplar
                    ex_fields = {
                        f: ex.get(f, "")
                        for f in self.fields_to_generate
                        if f in ex
                    }
                    hint_lines.append(f"    {json.dumps(ex_fields)}")

        hints_str = "\n".join(hint_lines) if hint_lines else "  (none)"

        prompt = f"""You are a synthetic data generator.

Generate a JSON object with the following fields: {fields_str}

CONSTRAINTS (must follow exactly):
{constraints_str}

HINTS (use as guidance):
{hints_str}

Return ONLY valid JSON with the requested fields, no markdown formatting or explanations."""

        return prompt

    def _parse_json_safely(self, content: str) -> dict[str, Any]:
        """
        parse JSON from LLM response
        handles markdown code blocks and other common patterns
        """
        # first try direct parsing
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # try extracting from markdown code block
        json_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # try extracting anything that looks like JSON
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        raise BlockExecutionError(
            "LLM returned invalid JSON",
            detail={
                "content": content[:500],  # first 500 chars
                "hint": "LLM should return pure JSON without markdown or explanations",
            },
        )

    async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
        from app import llm_config_manager

        # extract skeleton from context
        skeleton = context.accumulated_state.copy()
        hints = skeleton.pop("_hints", {})
        skeleton.pop("_usage", None)  # remove internal fields

        # build generation prompt
        prompt = self._build_generation_prompt(skeleton, hints)

        # prepare system prompt
        system_content = (
            self.system_prompt
            if self.system_prompt
            else "You are a synthetic data generator that produces realistic, diverse records."
        )

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt},
        ]

        # get LLM config
        llm_config = await llm_config_manager.get_llm_model(self.model_name)
        llm_params = llm_config_manager.prepare_llm_call(
            llm_config,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        # add trace metadata
        llm_params["metadata"] = {
            "trace_id": context.trace_id,
            "tags": ["datagenflow", "semantic-infiller"],
        }

        logger.info(
            f"Generating fields {self.fields_to_generate} with model={llm_params.get('model')}"
        )

        try:
            response = await litellm.acompletion(**llm_params)
        except Exception as e:
            raise BlockExecutionError(
                f"LLM call failed: {str(e)}",
                detail={
                    "skeleton": skeleton,
                    "prompt_preview": prompt[:200],
                    "error": str(e),
                },
            )

        # parse response
        content = response.choices[0].message.content
        try:
            generated = self._parse_json_safely(content)
        except BlockExecutionError as e:
            logger.error(f"Failed to parse JSON: {e.message}")
            raise

        # validate that LLM didn't modify skeleton fields
        for field, value in skeleton.items():
            if field in generated and generated[field] != value:
                logger.warning(
                    f"LLM modified locked field '{field}': expected {value}, got {generated[field]}. "
                    f"Restoring original value."
                )
                generated[field] = value

        # merge skeleton + generated
        result = {**skeleton, **generated}

        # extract usage
        usage_info = pipeline.Usage(
            input_tokens=response.usage.prompt_tokens or 0,
            output_tokens=response.usage.completion_tokens or 0,
            cached_tokens=getattr(response.usage, "cache_read_input_tokens", 0) or 0,
        )

        result["_usage"] = usage_info.model_dump()

        logger.info(
            f"Generated {len(generated)} fields "
            f"(tokens: {usage_info.input_tokens}+{usage_info.output_tokens})"
        )

        return result
