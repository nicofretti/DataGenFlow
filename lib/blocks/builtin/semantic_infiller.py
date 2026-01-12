import asyncio
import json
import logging
from typing import Any

import litellm

from lib.blocks.base import BaseBlock
from lib.blocks.commons.template_utils import (
    clean_internal_fields,
    clean_metadata_fields,
    normalize_template_param,
    parse_llm_json_response,
    render_and_parse_json,
    validate_string_list,
)
from lib.entities import pipeline
from lib.entities.block_execution_context import BlockExecutionContext
from lib.errors import BlockExecutionError
from lib.template_renderer import render_template

logger = logging.getLogger(__name__)


class SemanticInfiller(BaseBlock):
    name = "Semantic Infiller"
    description = "Complete skeleton records using LLM to generate free-text fields"
    category = "generators"
    inputs = ["skeletons"]
    outputs = ["samples"]

    # constants for prompt generation
    MAX_EXEMPLARS_IN_PROMPT = 2

    _config_descriptions = {
        "fields_to_generate": (
            'JSON array or Jinja template. Examples: ["bio", "storage"] or {{ fields_to_generate | tojson }}'
        ),
        "model": "Select LLM model to use (leave empty for default)",
        "temperature": "Sampling temperature (0.0 = deterministic, 1.0 = creative)",
        "max_tokens": "Maximum tokens for generated response",
        "system_prompt": "Custom system prompt (optional, overrides default)",
    }

    _config_formats = {
        "fields_to_generate": "json-or-template",
    }

    def __init__(
        self,
        fields_to_generate: str | list[str],
        model: str | None = None,
        temperature: float = 0.8,
        max_tokens: int = 500,
        system_prompt: str = "",
    ):
        self.fields_to_generate_template = normalize_template_param(fields_to_generate, list)
        self.model_name = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt

    def _build_generation_prompt(
        self,
        fields_to_generate: list[str],
        skeleton: dict[str, Any],
        hints: dict[str, Any],
    ) -> str:
        """
        construct LLM prompt with constraints and hints

        format:
        - specify fields to generate
        - lock categorical constraints from skeleton
        - provide numeric hints and exemplars
        """
        fields_str = ", ".join(f'"{field}"' for field in fields_to_generate)

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
                for ex in value[: self.MAX_EXEMPLARS_IN_PROMPT]:
                    # only show generated fields from exemplar
                    ex_fields = {f: ex.get(f, "") for f in fields_to_generate if f in ex}
                    hint_lines.append(f"    {json.dumps(ex_fields)}")

        hints_str = "\n".join(hint_lines) if hint_lines else "  (none)"

        prompt = f"""You are a synthetic data generator. Create NEW and DIVERSE content - do NOT copy the examples.

Generate a JSON object with the following fields: {fields_str}

CONSTRAINTS (must follow exactly):
{constraints_str}

HINTS (for inspiration only - create variations, NOT copies):
{hints_str}

Return ONLY valid JSON with the requested fields, no markdown formatting or explanations."""

        return prompt

    async def _process_skeleton(
        self,
        skeleton_raw: dict[str, Any],
        fields_to_generate: list[str],
        llm_config: Any,
        context: BlockExecutionContext,
    ) -> dict[str, Any]:
        """process single skeleton to generate complete sample"""
        from app import llm_config_manager

        # clean skeleton and extract hints
        skeleton = clean_internal_fields(skeleton_raw)
        hints = skeleton_raw.get("_hints", {})
        skeleton = clean_metadata_fields(skeleton)

        # build prompt
        prompt = self._build_generation_prompt(fields_to_generate, skeleton, hints)

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

        # prepare LLM call
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

        # parse response using utility
        content = response.choices[0].message.content
        generated = parse_llm_json_response(content, "fields_to_generate")

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

        return result

    async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
        from app import llm_config_manager

        # extract skeletons from input
        skeletons = context.accumulated_state.get("skeletons", [])
        if not skeletons:
            raise BlockExecutionError("No skeletons provided in input")

        # parse fields_to_generate using utility
        fields_to_generate = render_and_parse_json(
            self.fields_to_generate_template,
            context.accumulated_state,
            "fields_to_generate",
            expected_type=list,
        )
        validate_string_list(fields_to_generate, "fields_to_generate")

        # get LLM config once (reuse for all skeletons)
        llm_config = await llm_config_manager.get_llm_model(self.model_name)

        logger.info(
            f"Processing {len(skeletons)} skeletons to generate fields {fields_to_generate} "
            f"with model={llm_config.get('model')}"
        )

        # process all skeletons in parallel
        tasks = [
            self._process_skeleton(skeleton, fields_to_generate, llm_config, context)
            for skeleton in skeletons
        ]
        samples = await asyncio.gather(*tasks)

        logger.info(f"Successfully generated {len(samples)} samples")

        return {"samples": samples}
