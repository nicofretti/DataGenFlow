import asyncio
import json
import logging
from typing import Any, cast

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

logger = logging.getLogger(__name__)


class SemanticInfiller(BaseBlock):
    name = "Semantic Infiller"
    description = "Complete skeleton records using LLM to generate free-text fields"
    category = "generators"
    inputs = ["skeletons"]
    outputs = ["samples"]

    # constant for prompt generation
    MAX_EXEMPLARS_IN_PROMPT = 2

    _config_descriptions = {
        "fields_to_generate": (
            "JSON array or Jinja template. "
            'Examples: ["bio", "storage"] or {{ fields_to_generate | tojson }}'
        ),
        "model": "Select LLM model to use (leave empty for default)",
        "temperature": "Sampling temperature (0.0 = deterministic, 1.0 = creative)",
        "max_tokens": "Maximum tokens for generated response",
        "system_prompt": "Custom system prompt (optional, overrides default)",
        "embedding_model": "Embedding model for diversity check (leave empty for default)",
        "diversity_threshold": (
            "Similarity threshold (0.0-1.0) above which samples are regenerated. "
            "Set to 1.0 to disable diversity check."
        ),
        "negative_examples_count": "Number of similar samples to show as negative examples",
        "max_diversity_retries": "Max retries per sample for diversity (0 to disable)",
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
        embedding_model: str | None = None,
        diversity_threshold: float = 0.85,
        negative_examples_count: int = 5,
        max_diversity_retries: int = 2,
    ):
        self.fields_to_generate_template = normalize_template_param(fields_to_generate, list)
        self.model_name = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt
        self.embedding_model_name = embedding_model
        self.diversity_threshold = diversity_threshold
        self.negative_examples_count = negative_examples_count
        self.max_diversity_retries = max_diversity_retries

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

        prompt = (
            "You are a synthetic data generator. "
            "Create NEW and DIVERSE content - do NOT copy the examples.\n\n"
            f"Generate a JSON object with the following fields: {fields_str}\n\n"
            f"CONSTRAINTS (must follow exactly):\n{constraints_str}\n\n"
            f"HINTS (for inspiration only - create variations, NOT copies):\n{hints_str}\n\n"
            "Return ONLY valid JSON with the requested fields, "
            "no markdown formatting or explanations."
        )

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
                    f"LLM modified locked field '{field}': "
                    f"expected {value}, got {generated[field]}. Restoring original value."
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

    def _extract_text_for_embedding(self, sample: dict[str, Any], fields: list[str]) -> str:
        """extract text from generated fields for embedding"""
        texts = []
        for field in fields:
            value = sample.get(field)
            if isinstance(value, str):
                texts.append(value)
        return " ".join(texts)

    async def _get_embedding(self, text: str, embedding_config: Any) -> list[float]:
        """get embedding vector for text"""
        from app import llm_config_manager

        params = llm_config_manager._prepare_embedding_call(embedding_config, input_text=text)
        response = await litellm.aembedding(**params)
        return cast(list[float], response.data[0]["embedding"])

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """compute cosine similarity between two vectors"""
        if len(vec1) != len(vec2):
            raise ValueError(f"Vector dimensions must match: {len(vec1)} vs {len(vec2)}")
        dot = sum(a * b for a, b in zip(vec1, vec2, strict=True))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return cast(float, dot / (norm1 * norm2))

    def _find_top_similar(
        self,
        target_embedding: list[float],
        embeddings: list[list[float]],
        samples: list[dict[str, Any]],
    ) -> list[tuple[float, dict[str, Any]]]:
        """find top N most similar samples by embedding similarity"""
        similarities = []
        for emb, sample in zip(embeddings, samples):
            sim = self._cosine_similarity(target_embedding, emb)
            similarities.append((sim, sample))

        similarities.sort(key=lambda x: x[0], reverse=True)
        return similarities[: self.negative_examples_count]

    def _build_diversity_prompt(
        self,
        fields_to_generate: list[str],
        skeleton: dict[str, Any],
        hints: dict[str, Any],
        similar_samples: list[tuple[float, dict[str, Any]]],
    ) -> str:
        """build prompt with negative examples to encourage diversity"""
        base_prompt = self._build_generation_prompt(fields_to_generate, skeleton, hints)

        if not similar_samples:
            return base_prompt

        negative_lines = []
        for sim, sample in similar_samples:
            fields_str = json.dumps({f: sample.get(f, "") for f in fields_to_generate})
            negative_lines.append(f"  - {fields_str}")

        return (
            base_prompt
            + "\n\nIMPORTANT - Your output was too similar to existing samples. "
            + "DO NOT generate content like these:\n"
            + "\n".join(negative_lines)
            + "\n\nCreate something COMPLETELY DIFFERENT and UNIQUE."
        )

    async def _generate_with_diversity_check(
        self,
        skeleton_raw: dict[str, Any],
        fields_to_generate: list[str],
        llm_config: Any,
        embedding_config: Any,
        existing_samples: list[dict[str, Any]],
        existing_embeddings: list[list[float]],
        context: BlockExecutionContext,
    ) -> tuple[dict[str, Any], list[float]]:
        """generate sample with diversity check and retry if too similar"""
        from app import llm_config_manager

        skeleton = clean_internal_fields(skeleton_raw)
        hints = skeleton_raw.get("_hints", {})
        skeleton = clean_metadata_fields(skeleton)

        similar_samples: list[tuple[float, dict[str, Any]]] = []

        for attempt in range(self.max_diversity_retries + 1):
            # build prompt (with negative examples after first attempt)
            if attempt == 0:
                prompt = self._build_generation_prompt(fields_to_generate, skeleton, hints)
            else:
                prompt = self._build_diversity_prompt(
                    fields_to_generate, skeleton, hints, similar_samples
                )

            system_content = (
                self.system_prompt
                if self.system_prompt
                else "You are a synthetic data generator that produces realistic, diverse records."
            )

            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt},
            ]

            llm_params = llm_config_manager.prepare_llm_call(
                llm_config,
                messages=messages,
                temperature=self.temperature + (attempt * 0.1),  # increase temp on retry
                max_tokens=self.max_tokens,
            )

            llm_params["metadata"] = {
                "trace_id": context.trace_id,
                "tags": ["datagenflow", "semantic-infiller"]
                + (["diversity-retry"] if attempt > 0 else []),
            }

            try:
                response = await litellm.acompletion(**llm_params)
            except Exception as e:
                raise BlockExecutionError(
                    f"LLM call failed: {str(e)}",
                    detail={"skeleton": skeleton, "attempt": attempt, "error": str(e)},
                )

            content = response.choices[0].message.content
            generated = parse_llm_json_response(content, "fields_to_generate")

            # restore locked fields
            for field, value in skeleton.items():
                if field in generated and generated[field] != value:
                    generated[field] = value

            result = {**skeleton, **generated}

            # get embedding for this sample
            text = self._extract_text_for_embedding(result, fields_to_generate)
            try:
                embedding = await self._get_embedding(text, embedding_config)
            except Exception as e:
                logger.warning(f"Embedding failed: {e}. Skipping diversity check.")
                embedding = []

            # check similarity to existing samples
            if embedding and existing_embeddings and self.diversity_threshold < 1.0:
                similar_samples = self._find_top_similar(
                    embedding, existing_embeddings, existing_samples
                )

                max_sim = similar_samples[0][0] if similar_samples else 0.0

                if max_sim >= self.diversity_threshold:
                    if attempt < self.max_diversity_retries:
                        logger.info(
                            f"Sample too similar ({max_sim:.2f}), "
                            f"retrying ({attempt + 1}/{self.max_diversity_retries})"
                        )
                        continue
                    else:
                        logger.warning(
                            f"Sample still similar ({max_sim:.2f}) "
                            f"after {self.max_diversity_retries} retries"
                        )

            # add usage info
            usage_info = pipeline.Usage(
                input_tokens=response.usage.prompt_tokens or 0,
                output_tokens=response.usage.completion_tokens or 0,
                cached_tokens=getattr(response.usage, "cache_read_input_tokens", 0) or 0,
            )
            result["_usage"] = usage_info.model_dump()

            return result, embedding

        # should not reach here, but return last result
        return result, embedding

    async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
        from app import llm_config_manager

        # extract skeletons from input
        skeletons = context.accumulated_state.get("skeletons", [])
        if not skeletons:
            raise BlockExecutionError(
                "No skeletons to process. This usually means StructureSampler didn't run "
                "or your seed data is missing required fields "
                "(samples, target_count, categorical_fields).",
                detail={"hint": "Check that your seed metadata contains the required fields"},
            )

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

        # check if diversity check is enabled
        diversity_enabled = self.diversity_threshold < 1.0 and self.max_diversity_retries > 0

        # try to get embedding config if diversity check is enabled
        embedding_config = None
        if diversity_enabled:
            try:
                embedding_config = await llm_config_manager.get_embedding_model(
                    self.embedding_model_name
                )
            except Exception as e:
                logger.warning(f"Embedding model unavailable: {e}. Disabling diversity check.")
                diversity_enabled = False

        logger.info(
            f"Processing {len(skeletons)} skeletons to generate fields {fields_to_generate} "
            f"with model={llm_config.model_name}, diversity_check={diversity_enabled}"
        )

        if diversity_enabled:
            # sequential processing with diversity check
            samples: list[dict[str, Any]] = []
            embeddings: list[list[float]] = []

            for i, skeleton in enumerate(skeletons):
                logger.debug(f"Processing skeleton {i + 1}/{len(skeletons)}")
                sample, embedding = await self._generate_with_diversity_check(
                    skeleton,
                    fields_to_generate,
                    llm_config,
                    embedding_config,
                    samples,
                    embeddings,
                    context,
                )
                samples.append(sample)
                if embedding:
                    embeddings.append(embedding)
        else:
            # parallel processing (faster, no diversity check)
            tasks = [
                self._process_skeleton(skeleton, fields_to_generate, llm_config, context)
                for skeleton in skeletons
            ]
            samples = await asyncio.gather(*tasks)

        logger.info(f"Successfully generated {len(samples)} samples")

        # aggregate usage from all samples
        total_usage = pipeline.Usage()
        for sample in samples:
            if "_usage" in sample:
                sample_usage = sample.pop("_usage")
                total_usage.input_tokens += sample_usage.get("input_tokens", 0)
                total_usage.output_tokens += sample_usage.get("output_tokens", 0)
                total_usage.cached_tokens += sample_usage.get("cached_tokens", 0)

        return {"samples": samples, "_usage": total_usage.model_dump()}
