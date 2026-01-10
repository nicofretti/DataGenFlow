from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lib.blocks.builtin.duplicate_remover import DuplicateRemover
from lib.entities.block_execution_context import BlockExecutionContext


def make_context(state: dict, initial_state: dict | None = None) -> BlockExecutionContext:
    """
    Create a BlockExecutionContext for tests, merging an optional initial state into the accumulated state.
    
    Parameters:
        state (dict): Base accumulated state for the context. If `initial_state` is provided, `state` is shallow-copied to avoid mutation.
        initial_state (dict | None): Optional mapping whose items are merged into the context's accumulated_state.
    
    Returns:
        BlockExecutionContext: A test context with trace_id "test-trace" and pipeline_id 1, whose accumulated_state contains `state` combined with `initial_state` (if given).
    """
    if initial_state:
        state = {**state}  # don't mutate
    context = BlockExecutionContext(
        trace_id="test-trace",
        pipeline_id=1,
        accumulated_state=state,
    )
    if initial_state:
        # add initial state items to accumulated_state
        context.accumulated_state.update(initial_state)
    return context


class TestDuplicateRemoverInit:
    def test_init_basic(self):
        block = DuplicateRemover()
        assert block.similarity_threshold == 0.85
        assert block.comparison_fields is None
        assert block.embedding_model_name is None

    def test_init_with_params(self):
        block = DuplicateRemover(
            similarity_threshold=0.9,
            comparison_fields=["bio", "description"],
            embedding_model="text-embedding-ada-002",
        )
        assert block.similarity_threshold == 0.9
        assert block.comparison_fields == ["bio", "description"]
        assert block.embedding_model_name == "text-embedding-ada-002"


class TestDuplicateRemoverTextExtraction:
    def test_extract_text_specific_fields(self):
        block = DuplicateRemover(comparison_fields=["bio"])

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

    def test_extract_text_handles_none(self):
        block = DuplicateRemover(comparison_fields=["bio"])

        record = {"bio": None, "other": "text"}
        text = block._extract_text(record, ["bio"])

        # None should be converted to empty string
        assert text == ""


class TestDuplicateRemoverNoSamples:
    @pytest.mark.asyncio
    async def test_no_samples_returns_not_duplicate(self):
        block = DuplicateRemover()

        context = make_context({"bio": "Test bio"})

        result = await block.execute(context)

        assert result["is_duplicate"] is False
        assert result["similarity_score"] == 0.0

    @pytest.mark.asyncio
    async def test_empty_samples_returns_not_duplicate(self):
        block = DuplicateRemover()

        context = make_context({"bio": "Test bio"}, {"samples": []})

        result = await block.execute(context)

        assert result["is_duplicate"] is False
        assert result["similarity_score"] == 0.0


class TestDuplicateRemoverNoText:
    @pytest.mark.asyncio
    async def test_no_text_returns_not_duplicate(self):
        block = DuplicateRemover(comparison_fields=["bio"])

        context = make_context({}, {"samples": [{"bio": "Sample"}]})

        result = await block.execute(context)

        assert result["is_duplicate"] is False
        assert result["similarity_score"] == 0.0


class TestDuplicateRemoverWithEmbeddings:
    @pytest.mark.asyncio
    @patch("litellm.aembedding")
    @patch("app.llm_config_manager")
    async def test_duplicate_detection_below_threshold(
        self, mock_config_manager, mock_embedding
    ):
        # setup mocks
        mock_config_manager.get_embedding_model = AsyncMock(
            return_value={"model": "text-embedding-ada-002"}
        )
        mock_config_manager._prepare_embedding_call = MagicMock(
            return_value={"model": "text-embedding-ada-002"}
        )

        # mock embeddings - different vectors (low similarity)
        mock_embedding.side_effect = [
            # reference embeddings
            MagicMock(data=[{"embedding": [1.0, 0.0, 0.0]}]),
            # current embedding
            MagicMock(data=[{"embedding": [0.0, 1.0, 0.0]}]),
        ]

        block = DuplicateRemover(
            similarity_threshold=0.85,
            comparison_fields=["bio"],
        )

        context = make_context(
            {"bio": "New unique bio"},
            {"samples": [{"bio": "Reference bio"}]},
        )

        result = await block.execute(context)

        assert result["is_duplicate"] is False
        assert result["similarity_score"] < 0.85

    @pytest.mark.asyncio
    @patch("litellm.aembedding")
    @patch("app.llm_config_manager")
    async def test_duplicate_detection_above_threshold(
        self, mock_config_manager, mock_embedding
    ):
        # setup mocks
        mock_config_manager.get_embedding_model = AsyncMock(
            return_value={"model": "text-embedding-ada-002"}
        )
        mock_config_manager._prepare_embedding_call = MagicMock(
            return_value={"model": "text-embedding-ada-002"}
        )

        # mock embeddings - very similar vectors (high similarity)
        mock_embedding.side_effect = [
            # reference embeddings
            MagicMock(data=[{"embedding": [1.0, 0.1, 0.0]}]),
            # current embedding (very similar)
            MagicMock(data=[{"embedding": [0.99, 0.11, 0.01]}]),
        ]

        block = DuplicateRemover(
            similarity_threshold=0.85,
            comparison_fields=["bio"],
        )

        context = make_context(
            {"bio": "Very similar bio"},
            {"samples": [{"bio": "Similar bio"}]},
        )

        result = await block.execute(context)

        assert result["is_duplicate"] is True
        assert result["similarity_score"] >= 0.85

    @pytest.mark.asyncio
    @patch("litellm.aembedding")
    @patch("app.llm_config_manager")
    async def test_embedding_cache_by_trace_id(
        self, mock_config_manager, mock_embedding
    ):
        """test that embeddings are cached per trace_id"""
        mock_config_manager.get_embedding_model = AsyncMock(
            return_value={"model": "text-embedding-ada-002"}
        )
        mock_config_manager._prepare_embedding_call = MagicMock(
            return_value={"model": "text-embedding-ada-002"}
        )

        mock_embedding.side_effect = [
            # first call - build reference embeddings
            MagicMock(data=[{"embedding": [1.0, 0.0, 0.0]}]),
            # second call - embed current text
            MagicMock(data=[{"embedding": [0.5, 0.5, 0.0]}]),
            # third call - embed second current text (reuses cache, so no reference embedding call)
            MagicMock(data=[{"embedding": [0.6, 0.4, 0.0]}]),
        ]

        block = DuplicateRemover(comparison_fields=["bio"])

        # first execution
        context1 = make_context(
            {"bio": "First bio"},
            {"samples": [{"bio": "Reference"}]},
        )
        await block.execute(context1)

        # second execution with same trace_id - should reuse cache
        context2 = make_context(
            {"bio": "Second bio"},
            {"samples": [{"bio": "Reference"}]},
        )
        context2.trace_id = "test-trace"  # same trace_id
        await block.execute(context2)

        # embedding should be called 3 times total (1 ref + 2 current)
        assert mock_embedding.call_count == 3


class TestDuplicateRemoverErrorHandling:
    @pytest.mark.asyncio
    async def test_no_embedding_model_skips_check(self):
        """test that missing embedding model gracefully skips check"""
        block = DuplicateRemover()

        context = make_context(
            {"bio": "Test bio"},
            {"samples": [{"bio": "Reference"}]},
        )

        # should not raise error
        result = await block.execute(context)

        assert result["is_duplicate"] is False
        assert result["similarity_score"] == 0.0

    @pytest.mark.asyncio
    @patch("app.llm_config_manager")
    async def test_embedding_error_skips_check(self, mock_config_manager):
        """test that embedding errors are caught and check is skipped"""
        mock_config_manager.get_embedding_model = AsyncMock(
            side_effect=Exception("Embedding model not found")
        )

        block = DuplicateRemover(embedding_model="invalid-model")

        context = make_context(
            {"bio": "Test bio"},
            {"samples": [{"bio": "Reference"}]},
        )

        # should not raise error
        result = await block.execute(context)

        assert result["is_duplicate"] is False
        assert result["similarity_score"] == 0.0


class TestDuplicateRemoverSchema:
    def test_schema_structure(self):
        schema = DuplicateRemover.get_schema()
        assert schema["name"] == "Duplicate Remover"
        assert schema["category"] == "validators"
        assert schema["inputs"] == ["*"]
        assert "*" in schema["outputs"]
        assert "is_duplicate" in schema["outputs"]
        assert "similarity_score" in schema["outputs"]

    def test_schema_has_required_configs(self):
        schema = DuplicateRemover.get_schema()
        config_props = schema["config_schema"]["properties"]
        assert "similarity_threshold" in config_props
        assert "comparison_fields" in config_props
        assert "embedding_model" in config_props