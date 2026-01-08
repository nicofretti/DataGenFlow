import logging
from typing import Any

import litellm
from sklearn.metrics.pairwise import cosine_similarity

from lib.blocks.base import BaseBlock
from lib.entities.block_execution_context import BlockExecutionContext

logger = logging.getLogger(__name__)


class DuplicateRemover(BaseBlock):
    name = "Duplicate Remover"
    description = "Flag records similar to reference dataset using embedding-based similarity"
    category = "validators"
    inputs = ["*"]
    outputs = ["*", "is_duplicate", "similarity_score"]

    _config_descriptions = {
        "similarity_threshold": "Similarity threshold (0.0-1.0). Above = duplicate.",
        "comparison_fields": "Fields to compare (leave empty to compare all text fields)",
        "embedding_model": "Embedding model to use (leave empty for default). Skips check if no model configured.",
    }

    def __init__(
        self,
        similarity_threshold: float = 0.85,
        comparison_fields: list[str] | None = None,
        embedding_model: str | None = None,
    ):
        self.similarity_threshold = similarity_threshold
        self.comparison_fields = comparison_fields
        self.embedding_model_name = embedding_model

        # cache reference embeddings (shared across records in same job)
        self._reference_embeddings: list[list[float]] = []
        self._embeddings_initialized = False

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
        current_text = self._extract_text(current_record, self.comparison_fields)

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

            # build reference embeddings (lazy, once per pipeline run)
            if not self._embeddings_initialized:
                logger.info(f"Building reference embeddings for {len(samples)} samples")

                sample_texts = [
                    self._extract_text(s, self.comparison_fields) for s in samples
                ]

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

                self._reference_embeddings = [item["embedding"] for item in response.data]
                self._embeddings_initialized = True

                logger.info(f"Initialized {len(self._reference_embeddings)} reference embeddings")

            # embed current text
            embedding_params = llm_config_manager._prepare_embedding_call(
                embedding_config, input_text=current_text
            )
            response = await litellm.aembedding(**embedding_params)
            current_embedding = response.data[0]["embedding"]

            # compute cosine similarities
            similarities = cosine_similarity(
                [current_embedding], self._reference_embeddings
            )[0]

            max_similarity = float(max(similarities)) if len(similarities) > 0 else 0.0
            is_duplicate = max_similarity >= self.similarity_threshold

            if is_duplicate:
                logger.warning(
                    f"Duplicate detected: similarity={max_similarity:.4f} >= {self.similarity_threshold}"
                )

        except Exception as e:
            # no embedding model configured or error - skip check
            logger.warning(
                f"Embedding check failed or no model configured: {e}. "
                f"Skipping similarity check."
            )
            is_duplicate = False
            max_similarity = 0.0

        return {
            **current_record,
            "is_duplicate": is_duplicate,
            "similarity_score": round(max_similarity, 4),
        }
