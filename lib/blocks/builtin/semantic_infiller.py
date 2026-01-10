import json
import logging
import re
from typing import Any

import litellm

from lib.blocks.base import BaseBlock
from lib.entities import pipeline
from lib.entities.block_execution_context import BlockExecutionContext
from lib.errors import BlockExecutionError
from lib.template_renderer import render_template

logger = logging.getLogger(__name__)


class SemanticInfiller(BaseBlock):
    name = "Semantic Infiller"
    description = "Complete skeleton records using LLM to generate free-text fields"
    category = "generators"
    inputs = ["*"]  # accepts any skeleton fields
    outputs = ["*"]  # returns merged skeleton + generated fields

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

    def __init__(
        self,
        fields_to_generate: str,
        model: str | None = None,
        temperature: float = 0.8,
        max_tokens: int = 500,
        system_prompt: str = "",
    ):
        """
        Initialize a SemanticInfiller with templates and LLM configuration.
        
        Parameters:
            fields_to_generate (str): A template (or JSON array template) specifying which field names the LLM should generate.
            model (str | None): Optional LLM model identifier to use; if None, a default model will be selected.
            temperature (float): Sampling temperature to control generation randomness; higher values make output more diverse.
            max_tokens (int): Maximum tokens the LLM is allowed to generate for the response.
            system_prompt (str): Optional system-level prompt prepended to the LLM conversation to guide behavior.
        """
        self.fields_to_generate_template = fields_to_generate
        self.model_name = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt

    def _build_generation_prompt(
        self, skeleton: dict[str, Any], hints: dict[str, Any]
    ) -> str:
        """
        Builds the LLM instruction prompt that requests generation of the specified free-text fields and includes locked constraints and optional hints.
        
        Parameters:
            skeleton (dict[str, Any]): Fixed field values from the input record; each key/value is presented as a constraint the model must not change.
            hints (dict[str, Any]): Optional guidance for generation. Keys ending with `_range` and a two-element list are interpreted as numeric range hints for the corresponding field (e.g., `"age_range": [18, 65]`). A key `"exemplars"` with a list of records is treated as example outputs; up to `MAX_EXEMPLARS_IN_PROMPT` exemplars are included and only the fields to generate are shown for each exemplar.
        
        Returns:
            str: A single prompt string instructing the model which fields to generate and providing CONSTRAINTS and HINTS sections; the prompt requests pure JSON output with only the requested fields.
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
                for ex in value[: self.MAX_EXEMPLARS_IN_PROMPT]:
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
        Extracts and parses JSON from an LLM response string.
        
        Attempts to parse `content` as JSON directly; if that fails, tries to extract JSON from a markdown code block (```json ... ```), then tries to extract any JSON-like `{...}` substring and parse it. Raises a BlockExecutionError if no valid JSON can be parsed.
        
        Parameters:
            content (str): Text returned by the LLM, which may contain raw JSON, a JSON code block, or surrounding explanatory text.
        
        Returns:
            dict[str, Any]: The parsed JSON object.
        
        Raises:
            BlockExecutionError: If no valid JSON can be extracted and parsed from `content`. The error includes a content snippet and a hint.
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
        """
        Generate the requested free-text fields for a skeleton record using an LLM and return the merged record.
        
        Builds a prompt from the provided skeleton and hints, renders and validates the configured fields_to_generate template, calls the LLM to produce a JSON object containing the requested fields, enforces immutability of existing skeleton fields (restoring any locked fields that the LLM changed), merges generated fields into the skeleton, attaches model usage metadata under the `_usage` key, and returns the resulting record.
        
        Returns:
            dict[str, Any]: The merged record containing the original skeleton fields, the generated fields, and an `_usage` entry with token usage metadata.
        
        Raises:
            BlockExecutionError: If `fields_to_generate` cannot be rendered as a valid JSON array of strings, if the LLM call fails, or if the LLM response cannot be parsed as JSON.
        """
        from app import llm_config_manager

        # extract skeleton from context
        skeleton = context.accumulated_state.copy()
        hints = skeleton.pop("_hints", {})
        skeleton.pop("_usage", None)  # remove internal fields

        # render fields_to_generate template and parse as JSON
        fields_template_rendered = render_template(
            self.fields_to_generate_template, context.accumulated_state
        )
        try:
            fields_to_generate = json.loads(fields_template_rendered)
            if not isinstance(fields_to_generate, list):
                raise BlockExecutionError(
                    "fields_to_generate must be a JSON array",
                    detail={"rendered_value": fields_template_rendered},
                )
            if not all(isinstance(f, str) for f in fields_to_generate):
                raise BlockExecutionError(
                    "All items in fields_to_generate must be strings",
                    detail={"fields_to_generate": fields_to_generate},
                )
        except json.JSONDecodeError as e:
            raise BlockExecutionError(
                f"fields_to_generate must be valid JSON: {str(e)}",
                detail={"template": self.fields_to_generate_template, "rendered": fields_template_rendered},
            )

        # temporarily set for prompt building
        self.fields_to_generate = fields_to_generate

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