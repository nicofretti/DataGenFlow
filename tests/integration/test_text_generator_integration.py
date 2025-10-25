import pytest

from lib.blocks.builtin.text_generator import TextGenerator


@pytest.mark.integration
@pytest.mark.asyncio
async def test_text_generator_ollama():
    """integration test for TextGenerator with actual Ollama instance"""
    block = TextGenerator(
        model="gemma3:1b",
        temperature=0.7,
        max_tokens=100,
        system_prompt="You are a helpful assistant",
        user_prompt="Say hello in one sentence",
    )

    result = await block.execute({})

    assert "assistant" in result
    assert "system" in result
    assert "user" in result
    assert len(result["assistant"]) > 0
    assert result["system"] == "You are a helpful assistant"
    assert result["user"] == "Say hello in one sentence"
    print(f"Generated response: {result['assistant']}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_text_generator_with_data():
    """integration test using prompts from data instead of config"""
    block = TextGenerator(temperature=0.5, max_tokens=50)

    result = await block.execute({"system": "Be concise", "user": "What is 2+2?"})

    assert "assistant" in result
    assert len(result["assistant"]) > 0
    print(f"Generated response: {result['assistant']}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_text_generator_no_system():
    """integration test with user prompt only"""
    block = TextGenerator(user_prompt="Tell me a fact about Python programming")

    result = await block.execute({})

    assert "assistant" in result
    assert len(result["assistant"]) > 0
    assert result["system"] == ""
    print(f"Generated response: {result['assistant']}")
