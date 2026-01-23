from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lib.blocks.builtin.semantic_infiller import SemanticInfiller
from lib.entities import LLMModelConfig, LLMProvider
from lib.entities.block_execution_context import BlockExecutionContext
from lib.errors import BlockExecutionError


def make_context(state: dict) -> BlockExecutionContext:
    """helper to create test context"""
    return BlockExecutionContext(
        trace_id="test-trace",
        pipeline_id=1,
        accumulated_state=state,
    )


class TestSemanticInfillerInit:
    def test_init_basic(self):
        block = SemanticInfiller(fields_to_generate='["bio"]')
        assert block.fields_to_generate_template == '["bio"]'
        assert block.model_name is None
        assert block.temperature == 0.8
        assert block.max_tokens == 500

    def test_init_with_all_params(self):
        block = SemanticInfiller(
            fields_to_generate='["bio", "description"]',
            model="gpt-4",
            temperature=0.9,
            max_tokens=1000,
            system_prompt="Custom prompt",
            embedding_model="text-embedding-ada-002",
            diversity_threshold=0.9,
            negative_examples_count=3,
            max_diversity_retries=5,
        )
        assert block.fields_to_generate_template == '["bio", "description"]'
        assert block.model_name == "gpt-4"
        assert block.temperature == 0.9
        assert block.max_tokens == 1000
        assert block.system_prompt == "Custom prompt"
        assert block.embedding_model_name == "text-embedding-ada-002"
        assert block.diversity_threshold == 0.9
        assert block.negative_examples_count == 3
        assert block.max_diversity_retries == 5

    def test_init_diversity_defaults(self):
        block = SemanticInfiller(fields_to_generate='["bio"]')
        assert block.embedding_model_name is None
        assert block.diversity_threshold == 0.85
        assert block.negative_examples_count == 5
        assert block.max_diversity_retries == 2

    def test_init_with_template(self):
        block = SemanticInfiller(fields_to_generate="{{ fields_to_generate }}")
        assert block.fields_to_generate_template == "{{ fields_to_generate }}"


class TestSemanticInfillerPromptBuilding:
    def test_build_prompt_with_constraints(self):
        block = SemanticInfiller(fields_to_generate='["bio"]')

        fields_to_generate = ["bio"]
        skeleton = {"plan": "Free", "role": "Viewer"}
        hints = {}

        prompt = block._build_generation_prompt(fields_to_generate, skeleton, hints)

        assert '"bio"' in prompt
        assert 'plan: "Free" (FIXED)' in prompt
        assert 'role: "Viewer" (FIXED)' in prompt

    def test_build_prompt_with_numeric_hints(self):
        block = SemanticInfiller(fields_to_generate='["storage"]')

        fields_to_generate = ["storage"]
        skeleton = {"plan": "Pro"}
        hints = {"storage_range": [10, 100]}

        prompt = block._build_generation_prompt(fields_to_generate, skeleton, hints)

        assert "storage should be between 10-100" in prompt

    def test_build_prompt_with_exemplars(self):
        block = SemanticInfiller(fields_to_generate='["bio"]')

        fields_to_generate = ["bio"]
        skeleton = {"plan": "Free"}
        hints = {
            "exemplars": [
                {"plan": "Free", "bio": "Student learning"},
                {"plan": "Free", "bio": "Just exploring"},
            ]
        }

        prompt = block._build_generation_prompt(fields_to_generate, skeleton, hints)

        assert "Example records" in prompt
        assert "Student learning" in prompt
        assert "Just exploring" in prompt


class TestSemanticInfillerDiversityPrompt:
    def test_build_diversity_prompt_with_negative_examples(self):
        block = SemanticInfiller(fields_to_generate='["bio"]')

        fields_to_generate = ["bio"]
        skeleton = {"plan": "Free"}
        hints = {}
        similar_samples = [
            (0.92, {"plan": "Free", "bio": "Similar bio 1"}),
            (0.88, {"plan": "Free", "bio": "Similar bio 2"}),
        ]

        prompt = block._build_diversity_prompt(fields_to_generate, skeleton, hints, similar_samples)

        assert "DO NOT generate content like these" in prompt
        assert "Similar bio 1" in prompt
        assert "Similar bio 2" in prompt
        assert "COMPLETELY DIFFERENT" in prompt

    def test_build_diversity_prompt_empty_similar_samples(self):
        block = SemanticInfiller(fields_to_generate='["bio"]')

        fields_to_generate = ["bio"]
        skeleton = {"plan": "Free"}
        hints = {}

        prompt = block._build_diversity_prompt(fields_to_generate, skeleton, hints, [])

        # should fall back to base prompt
        assert "DO NOT generate content like these" not in prompt
        assert '"bio"' in prompt


class TestSemanticInfillerTextExtraction:
    def test_extract_text_for_embedding(self):
        block = SemanticInfiller(fields_to_generate='["bio", "description"]')

        sample = {"bio": "Test bio", "description": "Test description", "count": 123}
        text = block._extract_text_for_embedding(sample, ["bio", "description"])

        assert "Test bio" in text
        assert "Test description" in text

    def test_extract_text_ignores_non_string_fields(self):
        block = SemanticInfiller(fields_to_generate='["bio"]')

        sample = {"bio": "Test bio", "count": 123, "active": True}
        text = block._extract_text_for_embedding(sample, ["bio", "count"])

        assert text == "Test bio"


class TestSemanticInfillerSimilarity:
    def test_cosine_similarity_identical_vectors(self):
        block = SemanticInfiller(fields_to_generate='["bio"]')

        sim = block._cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0])
        assert sim == 1.0

    def test_cosine_similarity_orthogonal_vectors(self):
        block = SemanticInfiller(fields_to_generate='["bio"]')

        sim = block._cosine_similarity([1.0, 0.0, 0.0], [0.0, 1.0, 0.0])
        assert sim == 0.0

    def test_cosine_similarity_zero_vector(self):
        block = SemanticInfiller(fields_to_generate='["bio"]')

        sim = block._cosine_similarity([0.0, 0.0, 0.0], [1.0, 0.0, 0.0])
        assert sim == 0.0

    def test_find_top_similar(self):
        block = SemanticInfiller(fields_to_generate='["bio"]', negative_examples_count=2)

        target = [1.0, 0.0, 0.0]
        embeddings = [
            [0.9, 0.1, 0.0],  # similar
            [0.0, 1.0, 0.0],  # different
            [0.8, 0.2, 0.0],  # somewhat similar
        ]
        samples = [{"bio": "Sample 1"}, {"bio": "Sample 2"}, {"bio": "Sample 3"}]

        top = block._find_top_similar(target, embeddings, samples)

        assert len(top) == 2
        # should be sorted by similarity descending
        assert top[0][1]["bio"] == "Sample 1"  # most similar


def _mock_llm_config():
    """helper to create test LLMModelConfig"""
    return LLMModelConfig(
        name="test",
        provider=LLMProvider.OPENAI,
        endpoint="http://test",
        model_name="gpt-4",
    )


class TestSemanticInfillerExecution:
    @pytest.mark.asyncio
    @patch("litellm.acompletion")
    @patch("app.llm_config_manager")
    async def test_execute_basic(self, mock_config_manager, mock_completion):
        # setup mocks
        mock_config_manager.get_llm_model = AsyncMock(return_value=_mock_llm_config())
        mock_config_manager.prepare_llm_call = MagicMock(
            return_value={"model": "gpt-4", "messages": []}
        )
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"bio": "Generated bio"}'))],
            usage=MagicMock(prompt_tokens=100, completion_tokens=50, cache_read_input_tokens=0),
        )

        block = SemanticInfiller(fields_to_generate='["bio"]')
        context = make_context({"skeletons": [{"plan": "Free", "role": "Viewer"}]})

        result = await block.execute(context)

        assert "samples" in result
        assert len(result["samples"]) == 1
        sample = result["samples"][0]
        assert sample["plan"] == "Free"
        assert sample["role"] == "Viewer"
        assert sample["bio"] == "Generated bio"
        assert "_usage" in result

    @pytest.mark.asyncio
    @patch("litellm.acompletion")
    @patch("app.llm_config_manager")
    async def test_execute_with_hints(self, mock_config_manager, mock_completion):
        # setup mocks
        mock_config_manager.get_llm_model = AsyncMock(return_value=_mock_llm_config())
        mock_config_manager.prepare_llm_call = MagicMock(
            return_value={"model": "gpt-4", "messages": []}
        )
        mock_completion.return_value = MagicMock(
            choices=[
                MagicMock(message=MagicMock(content='{"bio": "Generated bio", "storage": 50}'))
            ],
            usage=MagicMock(prompt_tokens=100, completion_tokens=50, cache_read_input_tokens=0),
        )

        block = SemanticInfiller(fields_to_generate='["bio", "storage"]')
        context = make_context(
            {"skeletons": [{"plan": "Pro", "_hints": {"storage_range": [10, 100]}}]}
        )

        result = await block.execute(context)

        assert "samples" in result
        sample = result["samples"][0]
        assert sample["bio"] == "Generated bio"
        assert sample["storage"] == 50
        # hints should be removed from result
        assert "_hints" not in sample

    @pytest.mark.asyncio
    @patch("litellm.acompletion")
    @patch("app.llm_config_manager")
    async def test_execute_restores_locked_fields(self, mock_config_manager, mock_completion):
        # LLM tries to modify a locked field
        mock_config_manager.get_llm_model = AsyncMock(return_value=_mock_llm_config())
        mock_config_manager.prepare_llm_call = MagicMock(
            return_value={"model": "gpt-4", "messages": []}
        )
        mock_completion.return_value = MagicMock(
            choices=[
                MagicMock(message=MagicMock(content='{"plan": "Modified", "bio": "Generated bio"}'))
            ],
            usage=MagicMock(prompt_tokens=100, completion_tokens=50, cache_read_input_tokens=0),
        )

        block = SemanticInfiller(fields_to_generate='["bio"]')
        context = make_context({"skeletons": [{"plan": "Free"}]})

        result = await block.execute(context)

        # plan should be restored to original value
        sample = result["samples"][0]
        assert sample["plan"] == "Free"
        assert sample["bio"] == "Generated bio"

    @pytest.mark.asyncio
    @patch("litellm.acompletion")
    @patch("app.llm_config_manager")
    async def test_execute_llm_error_raises(self, mock_config_manager, mock_completion):
        mock_config_manager.get_llm_model = AsyncMock(return_value=_mock_llm_config())
        mock_config_manager.prepare_llm_call = MagicMock(
            return_value={"model": "gpt-4", "messages": []}
        )
        mock_completion.side_effect = Exception("LLM API error")

        block = SemanticInfiller(fields_to_generate='["bio"]')
        context = make_context({"skeletons": [{"plan": "Free"}]})

        with pytest.raises(BlockExecutionError, match="LLM call failed"):
            await block.execute(context)

    @pytest.mark.asyncio
    @patch("litellm.acompletion")
    @patch("app.llm_config_manager")
    async def test_execute_with_template(self, mock_config_manager, mock_completion):
        """Test that Jinja templates work for fields_to_generate"""
        mock_config_manager.get_llm_model = AsyncMock(return_value=_mock_llm_config())
        mock_config_manager.prepare_llm_call = MagicMock(
            return_value={"model": "gpt-4", "messages": []}
        )
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"bio": "Generated bio"}'))],
            usage=MagicMock(prompt_tokens=100, completion_tokens=50, cache_read_input_tokens=0),
        )

        # Use tojson filter to properly serialize the list as JSON
        block = SemanticInfiller(fields_to_generate="{{ fields_to_generate | tojson }}")
        # Provide fields_to_generate in the accumulated state (from metadata)
        context = make_context({"skeletons": [{"plan": "Free"}], "fields_to_generate": ["bio"]})

        result = await block.execute(context)

        sample = result["samples"][0]
        assert sample["bio"] == "Generated bio"


class TestSemanticInfillerSchema:
    def test_schema_structure(self):
        schema = SemanticInfiller.get_schema()
        assert schema["name"] == "Semantic Infiller"
        assert schema["category"] == "generators"
        assert schema["inputs"] == ["skeletons"]
        assert schema["outputs"] == ["samples"]

    def test_schema_has_required_configs(self):
        schema = SemanticInfiller.get_schema()
        config_props = schema["config_schema"]["properties"]
        assert "fields_to_generate" in config_props
        assert "model" in config_props
        assert "temperature" in config_props
        assert "max_tokens" in config_props

    def test_schema_has_diversity_configs(self):
        schema = SemanticInfiller.get_schema()
        config_props = schema["config_schema"]["properties"]
        assert "embedding_model" in config_props
        assert "diversity_threshold" in config_props
        assert "negative_examples_count" in config_props
        assert "max_diversity_retries" in config_props


class TestSemanticInfillerDiversityExecution:
    @pytest.mark.asyncio
    @patch("litellm.aembedding")
    @patch("litellm.acompletion")
    @patch("app.llm_config_manager")
    async def test_execute_with_diversity_disabled(
        self, mock_config_manager, mock_completion, mock_embedding
    ):
        """when diversity_threshold=1.0, should skip diversity check and use parallel"""
        mock_config_manager.get_llm_model = AsyncMock(return_value=_mock_llm_config())
        mock_config_manager.prepare_llm_call = MagicMock(
            return_value={"model": "gpt-4", "messages": []}
        )
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"bio": "Generated bio"}'))],
            usage=MagicMock(prompt_tokens=100, completion_tokens=50, cache_read_input_tokens=0),
        )

        block = SemanticInfiller(
            fields_to_generate='["bio"]',
            diversity_threshold=1.0,  # disabled
        )
        context = make_context({"skeletons": [{"plan": "Free"}, {"plan": "Pro"}]})

        result = await block.execute(context)

        assert "samples" in result
        assert len(result["samples"]) == 2
        # embedding should NOT be called when diversity disabled
        mock_embedding.assert_not_called()

    @pytest.mark.asyncio
    @patch("litellm.aembedding")
    @patch("litellm.acompletion")
    @patch("app.llm_config_manager")
    async def test_execute_fallback_when_embedding_unavailable(
        self, mock_config_manager, mock_completion, mock_embedding
    ):
        """when embedding model unavailable, should fallback to parallel processing"""
        mock_config_manager.get_llm_model = AsyncMock(return_value=_mock_llm_config())
        mock_config_manager.get_embedding_model = AsyncMock(
            side_effect=Exception("Embedding model not configured")
        )
        mock_config_manager.prepare_llm_call = MagicMock(
            return_value={"model": "gpt-4", "messages": []}
        )
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content='{"bio": "Generated bio"}'))],
            usage=MagicMock(prompt_tokens=100, completion_tokens=50, cache_read_input_tokens=0),
        )

        block = SemanticInfiller(
            fields_to_generate='["bio"]',
            diversity_threshold=0.85,  # enabled
            max_diversity_retries=2,
        )
        context = make_context({"skeletons": [{"plan": "Free"}]})

        result = await block.execute(context)

        # should still work, just without diversity check
        assert "samples" in result
        assert len(result["samples"]) == 1

    @pytest.mark.asyncio
    @patch("litellm.aembedding")
    @patch("litellm.acompletion")
    @patch("app.llm_config_manager")
    async def test_execute_with_diversity_enabled(
        self, mock_config_manager, mock_completion, mock_embedding
    ):
        """when diversity enabled, should process sequentially with embedding check"""
        mock_config_manager.get_llm_model = AsyncMock(return_value=_mock_llm_config())
        mock_config_manager.get_embedding_model = AsyncMock(
            return_value={"model": "text-embedding-ada-002"}
        )
        mock_config_manager.prepare_llm_call = MagicMock(
            return_value={"model": "gpt-4", "messages": []}
        )
        mock_config_manager._prepare_embedding_call = MagicMock(
            return_value={"model": "text-embedding-ada-002"}
        )

        # mock LLM to return different bios
        mock_completion.side_effect = [
            MagicMock(
                choices=[MagicMock(message=MagicMock(content='{"bio": "First bio"}'))],
                usage=MagicMock(prompt_tokens=100, completion_tokens=50, cache_read_input_tokens=0),
            ),
            MagicMock(
                choices=[MagicMock(message=MagicMock(content='{"bio": "Second bio"}'))],
                usage=MagicMock(prompt_tokens=100, completion_tokens=50, cache_read_input_tokens=0),
            ),
        ]

        # mock embeddings to be different enough (below threshold)
        mock_embedding.side_effect = [
            MagicMock(data=[{"embedding": [1.0, 0.0, 0.0]}]),
            MagicMock(data=[{"embedding": [0.0, 1.0, 0.0]}]),
        ]

        block = SemanticInfiller(
            fields_to_generate='["bio"]',
            diversity_threshold=0.85,
            max_diversity_retries=2,
        )
        context = make_context({"skeletons": [{"plan": "Free"}, {"plan": "Pro"}]})

        result = await block.execute(context)

        assert "samples" in result
        assert len(result["samples"]) == 2
        assert result["samples"][0]["bio"] == "First bio"
        assert result["samples"][1]["bio"] == "Second bio"
        # embedding should be called for diversity check
        assert mock_embedding.call_count == 2
