from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lib.blocks.builtin.semantic_infiller import SemanticInfiller
from lib.entities import LLMModelConfig, LLMProvider
from lib.entities.block_execution_context import BlockExecutionContext
from lib.errors import BlockExecutionError


def make_context(state: dict) -> BlockExecutionContext:
    """
    Create a BlockExecutionContext for tests with fixed trace and pipeline identifiers.
    
    Parameters:
        state (dict): Accumulated state to embed in the returned context.
    
    Returns:
        BlockExecutionContext: Context with trace_id "test-trace", pipeline_id 1, and accumulated_state set to `state`.
    """
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
        )
        assert block.fields_to_generate_template == '["bio", "description"]'
        assert block.model_name == "gpt-4"
        assert block.temperature == 0.9
        assert block.max_tokens == 1000
        assert block.system_prompt == "Custom prompt"

    def test_init_with_template(self):
        block = SemanticInfiller(fields_to_generate="{{ fields_to_generate }}")
        assert block.fields_to_generate_template == "{{ fields_to_generate }}"


class TestSemanticInfillerPromptBuilding:
    def test_build_prompt_with_constraints(self):
        block = SemanticInfiller(fields_to_generate='["bio"]')
        # Set the parsed fields for prompt building
        block.fields_to_generate = ["bio"]

        skeleton = {"plan": "Free", "role": "Viewer"}
        hints = {}

        prompt = block._build_generation_prompt(skeleton, hints)

        assert '"bio"' in prompt
        assert 'plan: "Free" (FIXED)' in prompt
        assert 'role: "Viewer" (FIXED)' in prompt

    def test_build_prompt_with_numeric_hints(self):
        block = SemanticInfiller(fields_to_generate='["storage"]')
        block.fields_to_generate = ["storage"]

        skeleton = {"plan": "Pro"}
        hints = {"storage_range": [10, 100]}

        prompt = block._build_generation_prompt(skeleton, hints)

        assert "storage should be between 10-100" in prompt

    def test_build_prompt_with_exemplars(self):
        block = SemanticInfiller(fields_to_generate='["bio"]')
        block.fields_to_generate = ["bio"]

        skeleton = {"plan": "Free"}
        hints = {
            "exemplars": [
                {"plan": "Free", "bio": "Student learning"},
                {"plan": "Free", "bio": "Just exploring"},
            ]
        }

        prompt = block._build_generation_prompt(skeleton, hints)

        assert "Example records" in prompt
        assert "Student learning" in prompt
        assert "Just exploring" in prompt


class TestSemanticInfillerJSONParsing:
    def test_parse_valid_json(self):
        block = SemanticInfiller(fields_to_generate=["bio"])

        content = '{"bio": "Test bio"}'
        result = block._parse_json_safely(content)

        assert result == {"bio": "Test bio"}

    def test_parse_json_with_markdown(self):
        block = SemanticInfiller(fields_to_generate=["bio"])

        content = '```json\n{"bio": "Test bio"}\n```'
        result = block._parse_json_safely(content)

        assert result == {"bio": "Test bio"}

    def test_parse_json_embedded_in_text(self):
        block = SemanticInfiller(fields_to_generate=["bio"])

        content = 'Here is the result: {"bio": "Test bio"} done'
        result = block._parse_json_safely(content)

        assert result == {"bio": "Test bio"}

    def test_parse_invalid_json_raises_error(self):
        block = SemanticInfiller(fields_to_generate=["bio"])

        content = "not json at all"

        with pytest.raises(BlockExecutionError, match="invalid JSON"):
            block._parse_json_safely(content)


class TestSemanticInfillerExecution:
    @pytest.mark.asyncio
    @patch("litellm.acompletion")
    @patch("app.llm_config_manager")
    async def test_execute_basic(self, mock_config_manager, mock_completion):
        # setup mocks
        mock_config_manager.get_llm_model = AsyncMock(
            return_value=LLMModelConfig(
                name="test",
                provider=LLMProvider.OPENAI,
                endpoint="http://test",
                model_name="gpt-4",
            )
        )
        mock_config_manager.prepare_llm_call = MagicMock(
            return_value={"model": "gpt-4", "messages": []}
        )
        mock_completion.return_value = MagicMock(
            choices=[
                MagicMock(message=MagicMock(content='{"bio": "Generated bio"}'))
            ],
            usage=MagicMock(prompt_tokens=100, completion_tokens=50, cache_read_input_tokens=0),
        )

        block = SemanticInfiller(fields_to_generate='["bio"]')
        context = make_context({"plan": "Free", "role": "Viewer"})

        result = await block.execute(context)

        assert result["plan"] == "Free"
        assert result["role"] == "Viewer"
        assert result["bio"] == "Generated bio"
        assert "_usage" in result

    @pytest.mark.asyncio
    @patch("litellm.acompletion")
    @patch("app.llm_config_manager")
    async def test_execute_with_hints(self, mock_config_manager, mock_completion):
        # setup mocks
        mock_config_manager.get_llm_model = AsyncMock(
            return_value=LLMModelConfig(
                name="test",
                provider=LLMProvider.OPENAI,
                endpoint="http://test",
                model_name="gpt-4",
            )
        )
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
        context = make_context({
            "plan": "Pro",
            "_hints": {"storage_range": [10, 100]}
        })

        result = await block.execute(context)

        assert result["bio"] == "Generated bio"
        assert result["storage"] == 50
        # hints should be removed from result
        assert "_hints" not in result

    @pytest.mark.asyncio
    @patch("litellm.acompletion")
    @patch("app.llm_config_manager")
    async def test_execute_restores_locked_fields(self, mock_config_manager, mock_completion):
        # LLM tries to modify a locked field
        mock_config_manager.get_llm_model = AsyncMock(
            return_value=LLMModelConfig(
                name="test",
                provider=LLMProvider.OPENAI,
                endpoint="http://test",
                model_name="gpt-4",
            )
        )
        mock_config_manager.prepare_llm_call = MagicMock(
            return_value={"model": "gpt-4", "messages": []}
        )
        mock_completion.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content='{"plan": "Modified", "bio": "Generated bio"}'
                    )
                )
            ],
            usage=MagicMock(prompt_tokens=100, completion_tokens=50, cache_read_input_tokens=0),
        )

        block = SemanticInfiller(fields_to_generate='["bio"]')
        context = make_context({"plan": "Free"})

        result = await block.execute(context)

        # plan should be restored to original value
        assert result["plan"] == "Free"
        assert result["bio"] == "Generated bio"

    @pytest.mark.asyncio
    @patch("litellm.acompletion")
    @patch("app.llm_config_manager")
    async def test_execute_llm_error_raises(self, mock_config_manager, mock_completion):
        mock_config_manager.get_llm_model = AsyncMock(
            return_value=LLMModelConfig(
                name="test",
                provider=LLMProvider.OPENAI,
                endpoint="http://test",
                model_name="gpt-4",
            )
        )
        mock_config_manager.prepare_llm_call = MagicMock(
            return_value={"model": "gpt-4", "messages": []}
        )
        mock_completion.side_effect = Exception("LLM API error")

        block = SemanticInfiller(fields_to_generate='["bio"]')
        context = make_context({"plan": "Free"})

        with pytest.raises(BlockExecutionError, match="LLM call failed"):
            await block.execute(context)

    @pytest.mark.asyncio
    @patch("litellm.acompletion")
    @patch("app.llm_config_manager")
    async def test_execute_with_template(self, mock_config_manager, mock_completion):
        """Test that Jinja templates work for fields_to_generate"""
        mock_config_manager.get_llm_model = AsyncMock(
            return_value=LLMModelConfig(
                name="test",
                provider=LLMProvider.OPENAI,
                endpoint="http://test",
                model_name="gpt-4",
            )
        )
        mock_config_manager.prepare_llm_call = MagicMock(
            return_value={"model": "gpt-4", "messages": []}
        )
        mock_completion.return_value = MagicMock(
            choices=[
                MagicMock(message=MagicMock(content='{"bio": "Generated bio"}'))
            ],
            usage=MagicMock(prompt_tokens=100, completion_tokens=50, cache_read_input_tokens=0),
        )

        # Use tojson filter to properly serialize the list as JSON
        block = SemanticInfiller(fields_to_generate="{{ fields_to_generate | tojson }}")
        # Provide fields_to_generate in the accumulated state (from metadata)
        context = make_context({
            "plan": "Free",
            "fields_to_generate": ["bio"]
        })

        result = await block.execute(context)

        assert result["bio"] == "Generated bio"


class TestSemanticInfillerSchema:
    def test_schema_structure(self):
        schema = SemanticInfiller.get_schema()
        assert schema["name"] == "Semantic Infiller"
        assert schema["category"] == "generators"
        assert schema["inputs"] == ["*"]
        assert schema["outputs"] == ["*"]

    def test_schema_has_required_configs(self):
        schema = SemanticInfiller.get_schema()
        config_props = schema["config_schema"]["properties"]
        assert "fields_to_generate" in config_props
        assert "model" in config_props
        assert "temperature" in config_props
        assert "max_tokens" in config_props