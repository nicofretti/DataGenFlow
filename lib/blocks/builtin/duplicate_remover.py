import json
import logging
from typing import Any

import litellm
from sklearn.metrics.pairwise import cosine_similarity

from lib.blocks.base import BaseBlock
from lib.entities.block_execution_context import BlockExecutionContext
from lib.errors import BlockExecutionError
from lib.template_renderer import render_template

logger = logging.getLogger(__name__)


class DuplicateRemover(BaseBlock):
    name = "Duplicate Remover"
    description = "Flag records similar to reference dataset using embedding-based similarity"
    category = "validators"
    inputs = ["*"]
    outputs = ["*", "is_duplicate", "similarity_score"]

    _config_descriptions = {
        "similarity_threshold": "Similarity threshold (0.0-1.0). Above = duplicate.",
        "comparison_fields": (
            'JSON array or Jinja template. Examples: ["name", "bio"] or '
            '{{ comparison_fields | tojson }} (leave empty to compare all text fields)'
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
        # handle both string (from UI/templates with jinja) and list (from static YAML)
        if isinstance(comparison_fields, list):
            self.comparison_fields_template = json.dumps(comparison_fields)
        else:
            self.comparison_fields_template = comparison_fields if comparison_fields else ""
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

    async def execute(self, context: BlockExecutionContext) -> dict[str, Any]:
        from app import llm_config_manager

        # get current record from context
        current_record = context.accumulated_state.copy()
        current_record.pop("_usage", None)  # remove internal fields
        current_record.pop("_hints", None)

        # parse comparison_fields from template
        comparison_fields: list[str] | None = None
        if self.comparison_fields_template:
            fields_rendered = render_template(
                self.comparison_fields_template, context.accumulated_state
            )
            try:
                fields_list = json.loads(fields_rendered)
                if not isinstance(fields_list, list):
                    raise BlockExecutionError(
                        "comparison_fields must be a JSON array",
                        detail={"rendered_value": fields_rendered},
                    )
                if not all(isinstance(f, str) for f in fields_list):
                    raise BlockExecutionError(
                        "All items in comparison_fields must be strings",
                        detail={"comparison_fields": fields_list},
                    )
                comparison_fields = fields_list
            except json.JSONDecodeError as e:
                raise BlockExecutionError(
                    f"comparison_fields must be valid JSON: {str(e)}",
                    detail={
                        "template": self.comparison_fields_template,
                        "rendered": fields_rendered,
                    },
                )

        # get reference samples from initial state
        samples = context.get_state("samples", [])

        if not samples:
            logger.warning("No samples found for duplicate checking, marking as not duplicate")
            return {
                **current_record,
                "is_duplicate": False,
                "similarity_score": 0.0,
            }

        # extract text for comparison
        current_text = self._extract_text(current_record, comparison_fields)

        if not current_text:
            logger.warning("No text found in record for comparison, skipping check")
            return {
                **current_record,
                "is_duplicate": False,
                "similarity_score": 0.0,
            }

        try:
            # get embedding model
            embedding_config = await llm_config_manager.get_embedding_model(
                self.embedding_model_name
            )

            # get trace_id for cache key
            trace_id = context.trace_id

            # build reference embeddings (lazy, once per pipeline execution)
            if trace_id not in self._embeddings_cache:
                logger.info(f"Building reference embeddings for {len(samples)} samples")

                sample_texts = [self._extract_text(s, comparison_fields) for s in samples]

                # filter empty texts
                sample_texts = [t for t in sample_texts if t]

                if not sample_texts:
                    logger.warning("No valid sample texts for embedding, skipping check")
                    return {
                        **current_record,
                        "is_duplicate": False,
                        "similarity_score": 0.0,
                    }

                # embed all sample texts
                embedding_params = llm_config_manager._prepare_embedding_call(
                    embedding_config, input_text=sample_texts
                )
                response = await litellm.aembedding(**embedding_params)

                self._embeddings_cache[trace_id] = [item["embedding"] for item in response.data]

                logger.info(
                    f"Initialized {len(self._embeddings_cache[trace_id])} reference embeddings "
                    f"for trace_id={trace_id}"
                )

            # embed current text
            embedding_params = llm_config_manager._prepare_embedding_call(
                embedding_config, input_text=current_text
            )
            response = await litellm.aembedding(**embedding_params)
            current_embedding = response.data[0]["embedding"]

            # compute cosine similarities against cached embeddings
            reference_embeddings = self._embeddings_cache[trace_id]
            similarities = cosine_similarity([current_embedding], reference_embeddings)[0]

            max_similarity = float(max(similarities)) if len(similarities) > 0 else 0.0
            is_duplicate = max_similarity >= self.similarity_threshold

            if is_duplicate:
                logger.warning(
                    f"Duplicate detected: similarity={max_similarity:.4f} >= "
                    f"{self.similarity_threshold}"
                )

        except Exception as e:
            # no embedding model configured or error - skip check
            logger.warning(
                f"Embedding check failed or no model configured: {e}. Skipping similarity check."
            )
            is_duplicate = False
            max_similarity = 0.0

        return {
            **current_record,
            "is_duplicate": is_duplicate,
            "similarity_score": round(max_similarity, 4),
        }
