import pytest
from lib.blocks.builtin.text_generator import TextGenerator
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
@patch('litellm.acompletion')
async def test_text_generator_basic(mock_completion):
    mock_completion.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="Generated text"))]
    )

    block = TextGenerator(temperature=0.7, max_tokens=100)
    result = await block.execute({
        "system": "You are helpful",
        "user": "Hello"
    })

    assert "assistant" in result
    assert result["assistant"] == "Generated text"
    assert result["system"] == "You are helpful"
    assert result["user"] == "Hello"


@pytest.mark.asyncio
@patch('litellm.acompletion')
async def test_text_generator_with_prompts(mock_completion):
    mock_completion.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="Response"))]
    )

    block = TextGenerator(
        system_prompt="Be concise",
        user_prompt="Summarize AI"
    )
    result = await block.execute({})

    assert result["assistant"] == "Response"
    assert result["system"] == "Be concise"
    assert result["user"] == "Summarize AI"


@pytest.mark.asyncio
async def test_text_generator_schema():
    schema = TextGenerator.get_schema()
    assert schema["name"] == "Text Generator"
    assert "temperature" in schema["config_schema"]["properties"]
    assert "max_tokens" in schema["config_schema"]["properties"]
    assert "system_prompt" in schema["config_schema"]["properties"]
    assert "user_prompt" in schema["config_schema"]["properties"]
