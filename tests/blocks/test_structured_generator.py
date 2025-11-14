from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lib.blocks.builtin.structured_generator import StructuredGenerator
from models import LLMModelConfig, LLMProvider


@pytest.mark.asyncio
@patch("litellm.acompletion")
@patch("app.llm_config_manager")
async def test_structured_generator(mock_config_manager, mock_completion):
    mock_config_manager.get_llm_model = AsyncMock(
        return_value=LLMModelConfig(
            name="test", provider=LLMProvider.OPENAI, endpoint="http://test", model_name="gpt-4"
        )
    )
    mock_config_manager.prepare_llm_call = MagicMock(
        return_value={"model": "gpt-4", "messages": []}
    )
    # mock response with JSON
    mock_completion.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"name": "John", "age": 30}'))]
    )

    schema = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "number"}},
        "required": ["name", "age"],
    }

    block = StructuredGenerator(json_schema=schema)
    result = await block.execute({"user_prompt": "Generate person data"})

    assert "generated" in result
    assert result["generated"]["name"] == "John"
    assert result["generated"]["age"] == 30


@pytest.mark.asyncio
@patch("litellm.acompletion")
@patch("app.llm_config_manager")
async def test_structured_generator_with_prompt(mock_config_manager, mock_completion):
    mock_config_manager.get_llm_model = AsyncMock(
        return_value=LLMModelConfig(
            name="test", provider=LLMProvider.OPENAI, endpoint="http://test", model_name="gpt-4"
        )
    )
    mock_config_manager.prepare_llm_call = MagicMock(
        return_value={"model": "gpt-4", "messages": []}
    )
    mock_completion.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"result": "test"}'))]
    )

    schema = {"type": "object", "properties": {"result": {"type": "string"}}}

    block = StructuredGenerator(json_schema=schema, user_prompt="Generate a test result")
    result = await block.execute({})

    assert result["generated"]["result"] == "test"


@pytest.mark.asyncio
async def test_structured_generator_schema():
    schema_result = StructuredGenerator.get_schema()
    assert schema_result["name"] == "Structured Generator"
    assert "json_schema" in schema_result["config_schema"]["properties"]
    assert "temperature" in schema_result["config_schema"]["properties"]


@pytest.mark.asyncio
@patch("litellm.acompletion")
@patch("app.llm_config_manager")
async def test_structured_generator_with_enum_enforcement(mock_config_manager, mock_completion):
    """test that structured generator enforces enum values in schema"""
    mock_config_manager.get_llm_model = AsyncMock(
        return_value=LLMModelConfig(
            name="test", provider=LLMProvider.OPENAI, endpoint="http://test", model_name="gpt-4"
        )
    )
    mock_config_manager.prepare_llm_call = MagicMock(
        return_value={"model": "gpt-4", "messages": []}
    )
    # mock response with category from enum
    mock_completion.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content='{"category": "positive", "score": 0.9}'))]
    )

    schema = {
        "type": "object",
        "properties": {
            "category": {"type": "string", "enum": ["positive", "negative", "neutral"]},
            "score": {"type": "number"},
        },
        "required": ["category", "score"],
    }

    block = StructuredGenerator(
        json_schema=schema, user_prompt="Classify sentiment: Great product!", temperature=0.7
    )

    result = await block.execute({})
    generated = result["generated"]

    # verify structure
    assert "category" in generated
    assert "score" in generated

    # verify enum constraint (should be one of the allowed values)
    assert generated["category"] in ["positive", "negative", "neutral"]
    assert isinstance(generated["score"], (int, float))
