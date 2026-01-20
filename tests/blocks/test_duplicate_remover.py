from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lib.blocks.builtin.duplicate_remover import DuplicateRemover
from lib.entities.block_execution_context import BlockExecutionContext


def make_context(state: dict[str, Any]) -> BlockExecutionContext:
    """helper to create test context"""
    return BlockExecutionContext(
        trace_id="test-trace",
        pipeline_id=1,
        accumulated_state=state,
    )


class TestDuplicateRemoverInit:
    def test_init_basic(self):
        block = DuplicateRemover()
        assert block.similarity_threshold == 0.85
        assert block.comparison_fields_template == ""
        assert block.embedding_model_name is None

    def test_init_with_params(self):
        block = DuplicateRemover(
            similarity_threshold=0.9,
            comparison_fields='["bio", "description"]',
            embedding_model="text-embedding-ada-002",
        )
        assert block.similarity_threshold == 0.9
        assert block.comparison_fields_template == '["bio", "description"]'
        assert block.embedding_model_name == "text-embedding-ada-002"


class TestDuplicateRemoverTextExtraction:
    def test_extract_text_specific_fields(self):
        block = DuplicateRemover(comparison_fields='["bio"]')

        record = {"bio": "Test bio", "other": "Ignored"}
        text = block._extract_text(record, ["bio"])

        assert text == "Test bio"

    def test_extract_text_multiple_fields(self):
        block = DuplicateRemover(comparison_fields=["bio", "description"])

        record = {"bio": "Bio text", "description": "Description text"}
        text = block._extract_text(record, ["bio", "description"])

        assert text == "Bio text Description text"

    def test_extract_text_auto_detect(self):
        block = DuplicateRemover()

        record = {"bio": "Bio text", "plan": "Free", "count": 123}
        text = block._extract_text(record, None)

        # should only include string fields
        assert "Bio text" in text
        assert "Free" in text
        assert "123" not in text


class TestDuplicateRemoverNoSamples:
    @pytest.mark.asyncio
    async def test_no_seed_samples_returns_default_similarity(self):
        block = DuplicateRemover()

        context = make_context({"samples": [{"bio": "Test bio"}]})

        result = await block.execute(context)

        assert "generated_samples" in result
        assert len(result["generated_samples"]) == 1
        sample = result["generated_samples"][0]
        assert sample["is_duplicate"] is False
        assert sample["similarity_to_seeds"] == 0.0
        assert sample["similarity_to_generated"] == 0.0


class TestDuplicateRemoverWithEmbeddings:
    @pytest.mark.asyncio
    @patch("litellm.aembedding")
    @patch("app.llm_config_manager")
    async def test_duplicate_detection_batch(self, mock_config_manager, mock_embedding):
        # setup mocks
        mock_config_manager.get_embedding_model = AsyncMock(
            return_value={"model": "text-embedding-ada-002"}
        )
        mock_config_manager._prepare_embedding_call = MagicMock(
            return_value={"model": "text-embedding-ada-002"}
        )

        # mock embeddings
        # seed embeddings: [1,0,0]
        # sample 1: [0.99, 0.1, 0] - very similar to seed
        # sample 2: [0, 1, 0] - different from seed, but similar to sample 1
        mock_embedding.side_effect = [
            # seed embeddings
            MagicMock(data=[{"embedding": [1.0, 0.0, 0.0]}]),
            # batch embeddings for 2 samples
            MagicMock(
                data=[
                    {"embedding": [0.99, 0.1, 0.0]},
                    {"embedding": [0.0, 1.0, 0.0]},
                ]
            ),
        ]

        block = DuplicateRemover(
            similarity_threshold=0.85,
            comparison_fields='["bio"]',
        )

        context = make_context({"samples": [{"bio": "Very similar bio"}, {"bio": "Different bio"}]})

        result = await block.execute(context)

        assert "generated_samples" in result
        assert len(result["generated_samples"]) == 2

        # check that similarity fields are present
        sample1 = result["generated_samples"][0]
        assert "similarity_to_seeds" in sample1
        assert "similarity_to_generated" in sample1
        assert "is_duplicate" in sample1

        # second sample
        sample2 = result["generated_samples"][1]
        assert "similarity_to_seeds" in sample2
        assert "similarity_to_generated" in sample2
        assert "is_duplicate" in sample2

    @pytest.mark.asyncio
    @patch("litellm.aembedding")
    @patch("app.llm_config_manager")
    async def test_dual_similarity_computation(self, mock_config_manager, mock_embedding):
        """test that both similarity_to_seeds and similarity_to_generated are computed"""
        mock_config_manager.get_embedding_model = AsyncMock(
            return_value={"model": "text-embedding-ada-002"}
        )
        mock_config_manager._prepare_embedding_call = MagicMock(
            return_value={"model": "text-embedding-ada-002"}
        )

        # seed: [1,0,0]
        # sample1: [0,1,0] - different from seed
        # sample2: [0,0.9,0.1] - different from seed but very similar to sample1
        mock_embedding.side_effect = [
            MagicMock(data=[{"embedding": [1.0, 0.0, 0.0]}]),
            MagicMock(
                data=[
                    {"embedding": [0.0, 1.0, 0.0]},
                    {"embedding": [0.0, 0.9, 0.1]},
                ]
            ),
        ]

        block = DuplicateRemover(
            similarity_threshold=0.85,
            comparison_fields='["bio"]',
        )

        context = make_context({"samples": [{"bio": "Sample 1"}, {"bio": "Sample 2 similar to 1"}]})

        result = await block.execute(context)

        # check that samples have similarity fields
        samples = result["generated_samples"]
        assert len(samples) == 2

        # check that similarity_to_generated is computed (samples compared to each other)
        assert (
            samples[0]["similarity_to_generated"] > 0.0
            or samples[1]["similarity_to_generated"] > 0.0
        )

    @pytest.mark.asyncio
    @patch("litellm.aembedding")
    @patch("app.llm_config_manager")
    async def test_embedding_cache_by_trace_id(self, mock_config_manager, mock_embedding):
        """test that seed embeddings are cached per trace_id"""
        mock_config_manager.get_embedding_model = AsyncMock(
            return_value={"model": "text-embedding-ada-002"}
        )
        mock_config_manager._prepare_embedding_call = MagicMock(
            return_value={"model": "text-embedding-ada-002"}
        )

        mock_embedding.side_effect = [
            # first call - build seed embeddings
            MagicMock(data=[{"embedding": [1.0, 0.0, 0.0]}]),
            # second call - batch samples
            MagicMock(data=[{"embedding": [0.5, 0.5, 0.0]}]),
            # third call - second batch (reuses seed cache)
            MagicMock(data=[{"embedding": [0.6, 0.4, 0.0]}]),
        ]

        block = DuplicateRemover(comparison_fields='["bio"]')

        # first execution
        context1 = make_context({"samples": [{"bio": "First bio"}]})
        await block.execute(context1)

        # second execution with same trace_id - should reuse cache
        context2 = make_context({"samples": [{"bio": "Second bio"}]})
        context2.trace_id = "test-trace"  # same trace_id
        await block.execute(context2)

        # embedding should be called 3 times total (1 seed + 2 batches)
        assert mock_embedding.call_count == 3


class TestDuplicateRemoverErrorHandling:
    @pytest.mark.asyncio
    async def test_no_embedding_model_returns_default(self):
        """test that missing embedding model gracefully returns defaults"""
        block = DuplicateRemover()

        context = make_context({"samples": [{"bio": "Test bio"}]})

        result = await block.execute(context)

        assert "generated_samples" in result
        sample = result["generated_samples"][0]
        assert sample["is_duplicate"] is False
        assert sample["similarity_to_seeds"] == 0.0
        assert sample["similarity_to_generated"] == 0.0

    @pytest.mark.asyncio
    @patch("app.llm_config_manager")
    async def test_embedding_error_returns_default(self, mock_config_manager):
        """test that embedding errors are caught and defaults returned"""
        mock_config_manager.get_embedding_model = AsyncMock(
            side_effect=Exception("Embedding model not found")
        )

        block = DuplicateRemover(embedding_model="invalid-model")

        context = make_context({"samples": [{"bio": "Test bio"}]})

        result = await block.execute(context)

        assert "generated_samples" in result
        sample = result["generated_samples"][0]
        assert sample["is_duplicate"] is False
        assert sample["similarity_to_seeds"] == 0.0


class TestDuplicateRemoverSchema:
    def test_schema_structure(self):
        schema = DuplicateRemover.get_schema()
        assert schema["name"] == "Duplicate Remover"
        assert schema["category"] == "validators"
        assert schema["inputs"] == ["samples"]
        assert schema["outputs"] == ["generated_samples"]

    def test_schema_has_required_configs(self):
        schema = DuplicateRemover.get_schema()
        config_props = schema["config_schema"]["properties"]
        assert "similarity_threshold" in config_props
        assert "comparison_fields" in config_props
        assert "embedding_model" in config_props
