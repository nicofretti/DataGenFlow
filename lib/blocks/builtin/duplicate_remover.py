import logging
from typing import Any

import litellm
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity  # type: ignore[import-untyped]

from lib.blocks.base import BaseBlock
from lib.blocks.commons.template_utils import (
    clean_internal_fields,
    normalize_template_param,
    render_and_parse_json,
    validate_string_list,
)
from lib.entities import pipeline
from lib.entities.block_execution_context import BlockExecutionContext
from lib.errors import BlockExecutionError

logger = logging.getLogger(__name__)


class DuplicateRemover(BaseBlock):
    name = "Duplicate Remover"
    description = "Flag records similar to reference dataset using embedding-based similarity"
    category = "validators"
    inputs = ["samples"]
    outputs = ["generated_samples"]

    _config_descriptions = {
        "similarity_threshold": "Similarity threshold (0.0-1.0). Above = duplicate.",
        "comparison_fields": (
            'JSON array or Jinja template. Examples: ["name", "bio"] or '
            "{{ comparison_fields | tojson }} (leave empty to compare all text fields)"
        ),
        "embedding_model": (
            "Embedding model to use (leave empty for default). Skips check if no model configured."
        ),
    }

    _config_formats = {
        "comparison_fields": "json-or-template",
    }

    def __init__(
        self,
        similarity_threshold: float = 0.85,
        comparison_fields: str | list[str] = "",
        embedding_model: str | None = None,
    ):
        self.similarity_threshold = similarity_threshold
        self.comparison_fields_template = (
            normalize_template_param(comparison_fields, list) if comparison_fields else ""
        )
        self.embedding_model_name = embedding_model

        # cache reference embeddings per trace_id (one cache per pipeline execution)
        self._embeddings_cache: dict[str, list[list[float]]] = {}

    def _extract_text(self, record: dict[str, Any], fields: list[str] | None) -> str:
        """
        extract text from specified fields or all string fields
        joins with spaces for embedding
        """
        if fields:
            texts = []
            for field in fields:
                value = record.get(field, "")
                if value is not None:
                    texts.append(str(value))
        else:
            # auto-detect string fields
            texts = []
            for value in record.values():
                if isinstance(value, str) and value:
                    texts.append(value)

        return " ".join(texts)

    async def _get_seed_embeddings(
        self,
        seed_samples: list[dict[str, Any]],
        comparison_fields: list[str] | None,
        embedding_config: Any,
        trace_id: str,
    ) -> tuple[list[list[float]], pipeline.Usage]:
        """get seed embeddings with trace_id caching, returns (embeddings, usage)"""
        from app import llm_config_manager

        zero_usage = pipeline.Usage()

        # check cache (no usage since already computed)
        if trace_id in self._embeddings_cache:
            return self._embeddings_cache[trace_id], zero_usage

        logger.info(f"Building reference embeddings for {len(seed_samples)} seed samples")

        # extract and embed seed texts
        seed_texts = [self._extract_text(s, comparison_fields) for s in seed_samples]
        seed_texts = [t for t in seed_texts if t]

        if not seed_texts:
            return [], zero_usage

        embedding_params = llm_config_manager._prepare_embedding_call(
            embedding_config,
            input_text=seed_texts,  # type: ignore[arg-type]
        )
        response = await litellm.aembedding(**embedding_params)

        # extract usage from embedding response
        usage = pipeline.Usage(
            input_tokens=getattr(response.usage, "prompt_tokens", 0) or 0,
            output_tokens=0,  # embeddings don't have output tokens
            cached_tokens=getattr(response.usage, "cache_read_input_tokens", 0) or 0,
        )

        # cache by trace_id
        self._embeddings_cache[trace_id] = [item["embedding"] for item in response.data]
        logger.info(f"Cached {len(self._embeddings_cache[trace_id])} seed embeddings")

        return self._embeddings_cache[trace_id], usage

    def _compute_similarities(
        self,
        samples: list[dict[str, Any]],
        sample_embeddings: list[list[float]],
        seed_embeddings: list[list[float]],
    ) -> list[dict[str, Any]]:
        """compute dual similarity scores for each sample"""
        n = len(sample_embeddings)

        # similarity to seeds (each sample vs all seeds)
        seed_sims = cosine_similarity(sample_embeddings, seed_embeddings)
        similarity_to_seeds = seed_sims.max(axis=1)  # max per row

        # similarity to other generated samples (exclude self)
        if n > 1:
            batch_sims = cosine_similarity(sample_embeddings, sample_embeddings)
            np.fill_diagonal(batch_sims, -1)  # ignore self-similarity
            similarity_to_generated = batch_sims.max(axis=1)
        else:
            similarity_to_generated = np.zeros(n)

        # enrich samples (strip internal fields like _usage, _hints)
        enriched = []
        for i, sample in enumerate(samples):
            sim_to_seeds = float(similarity_to_seeds[i])
            sim_to_generated = float(similarity_to_generated[i])

            enriched.append(
                {
                    **clean_internal_fields(sample),
                    "similarity_to_seeds": round(sim_to_seeds, 4),
                    "similarity_to_generated": round(sim_to_generated, 4),
                    "is_duplicate": (
                        sim_to_seeds >= self.similarity_threshold
                        or sim_to_generated >= self.similarity_threshold
                    ),
                }
            )

        return enriched

    def _add_default_similarity(self, samples: list[dict[str, Any]]) -> dict[str, Any]:
        """add default similarity values when embeddings unavailable"""
        enriched = [
            {
                **clean_internal_fields(sample),
                "similarity_to_seeds": 0.0,
                "similarity_to_generated": 0.0,
                "is_duplicate": False,
            }
            for sample in samples
        ]
        return {"generated_samples": enriched}

    async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
        from app import llm_config_manager

        # extract samples from input
        samples = context.accumulated_state.get("samples", [])
        if not samples:
            raise BlockExecutionError("No samples provided in input")

        # parse comparison_fields
        comparison_fields = None
        if self.comparison_fields_template:
            comparison_fields = render_and_parse_json(
                self.comparison_fields_template,
                context.accumulated_state,
                "comparison_fields",
                expected_type=list,
            )
            validate_string_list(comparison_fields, "comparison_fields")

        # get original seed samples (preserved by StructureSampler as _seed_samples)
        seed_samples = context.get_state("_seed_samples", [])
        if not seed_samples:
            # fallback to samples from metadata (for standalone use)
            seed_samples = context.get_state("samples", [])
        if not seed_samples:
            logger.warning("No seed samples for duplicate checking")
            return self._add_default_similarity(samples)

        try:
            # get embedding model
            embedding_config = await llm_config_manager.get_embedding_model(
                self.embedding_model_name
            )

            # get seed embeddings (cached by trace_id)
            seed_embeddings, seed_usage = await self._get_seed_embeddings(
                seed_samples, comparison_fields, embedding_config, context.trace_id
            )

            # get batch embeddings for generated samples
            sample_texts = [
                self._extract_text(clean_internal_fields(s), comparison_fields) for s in samples
            ]
            sample_texts = [t for t in sample_texts if t]

            if not sample_texts:
                return self._add_default_similarity(samples)

            # embed all generated samples at once
            embedding_params = llm_config_manager._prepare_embedding_call(
                embedding_config,
                input_text=sample_texts,  # type: ignore[arg-type]
            )
            response = await litellm.aembedding(**embedding_params)
            sample_embeddings = [item["embedding"] for item in response.data]

            # extract usage from sample embeddings
            sample_usage = pipeline.Usage(
                input_tokens=getattr(response.usage, "prompt_tokens", 0) or 0,
                output_tokens=0,
                cached_tokens=getattr(response.usage, "cache_read_input_tokens", 0) or 0,
            )

            # accumulate total usage
            total_usage = pipeline.Usage(
                input_tokens=seed_usage.input_tokens + sample_usage.input_tokens,
                output_tokens=0,
                cached_tokens=seed_usage.cached_tokens + sample_usage.cached_tokens,
            )

            # compute dual similarities
            enriched_samples = self._compute_similarities(
                samples,
                sample_embeddings,
                seed_embeddings,
            )

            logger.info(
                f"Checked {len(samples)} samples for duplicates. "
                f"Found {sum(1 for s in enriched_samples if s['is_duplicate'])} duplicates."
            )

            return {"generated_samples": enriched_samples, "_usage": total_usage.model_dump()}

        except Exception as e:
            logger.warning(f"Embedding check failed: {e}. Skipping.")
            return self._add_default_similarity(samples)
