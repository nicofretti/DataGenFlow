"""
tests for LLM generator wrapper
"""

from unittest.mock import AsyncMock, patch

import pytest

from lib.generator import Generator
from models import GenerationConfig


@pytest.mark.asyncio
async def test_generator_initializes_with_config():
    """generator should accept and store config"""
    config = GenerationConfig(model="test-model", temperature=0.8)
    gen = Generator(config)

    assert gen.config.model == "test-model"
    assert gen.config.temperature == 0.8


@pytest.mark.asyncio
async def test_generator_calls_llm_endpoint():
    """generator should call llm endpoint with system and user prompts"""
    config = GenerationConfig(model="test-model")
    gen = Generator(config)

    with patch("httpx.AsyncClient") as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = lambda: {"choices": [{"message": {"content": "test response"}}]}
        mock_response.raise_for_status = lambda: None

        mock_post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.post = mock_post

        result = await gen.generate("system prompt", "user prompt")

        assert result == "test response"
        mock_post.assert_called_once()
