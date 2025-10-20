"""
Tests for LLMBlock in lib/blocks/builtin/llm.py
"""

from unittest.mock import AsyncMock, patch

import pytest

from lib.blocks.builtin.llm import LLMBlock


class TestLLMBlock:
    """Test LLM block functionality"""

    def test_llm_block_init(self):
        """Test LLMBlock initialization"""
        block = LLMBlock(model="test-model", temperature=0.5, max_tokens=1024)
        assert block.model == "test-model"
        assert block.temperature == 0.5
        assert block.max_tokens == 1024

        # test with default values
        block_default = LLMBlock()
        assert block_default.model is None
        assert block_default.temperature == 0.7
        assert block_default.max_tokens == 2048

    def test_llm_block_schema(self):
        """Test LLMBlock schema generation"""
        block = LLMBlock()
        schema = block.get_schema()

        assert "type" in schema
        assert schema["type"] == "LLMBlock"
        assert "name" in schema
        assert schema["name"] == "LLM Generator"
        assert "inputs" in schema
        assert schema["inputs"] == ["system", "user"]
        assert "outputs" in schema
        assert schema["outputs"] == ["assistant", "system", "user"]

    @pytest.mark.asyncio
    async def test_llm_block_execute_success(self):
        """Test LLMBlock execution with mocked LLM response"""
        block = LLMBlock(model="test-model")

        # mock generator.generate
        with patch("lib.blocks.builtin.llm.Generator") as mock_generator:
            mock_instance = mock_generator.return_value
            mock_instance.generate = AsyncMock(return_value="This is a test response")

            input_data = {"system": "You are a helpful assistant", "user": "Say hello"}

            result = await block.execute(input_data)

            # check result
            assert "assistant" in result
            assert result["assistant"] == "This is a test response"

            # check generator was called
            mock_instance.generate.assert_called_once_with(
                "You are a helpful assistant", "Say hello"
            )

    @pytest.mark.asyncio
    async def test_llm_block_execute_with_error(self):
        """Test LLMBlock execution when LLM call fails"""
        block = LLMBlock(model="test-model")

        # mock generator to raise exception
        with patch("lib.blocks.builtin.llm.Generator") as mock_generator:
            mock_instance = mock_generator.return_value
            mock_instance.generate = AsyncMock(side_effect=Exception("LLM API error"))

            input_data = {"system": "You are a helpful assistant", "user": "Say hello"}

            with pytest.raises(Exception):
                await block.execute(input_data)

    @pytest.mark.asyncio
    async def test_llm_block_execute_missing_fields(self):
        """Test LLMBlock execution with missing fields"""
        block = LLMBlock()

        # missing fields default to empty strings
        with patch("lib.blocks.builtin.llm.Generator") as mock_generator:
            mock_instance = mock_generator.return_value
            mock_instance.generate = AsyncMock(return_value="response")

            # test with missing system
            result = await block.execute({"user": "Say hello"})
            assert result["assistant"] == "response"
            mock_instance.generate.assert_called_with("", "Say hello")

            # test with missing user
            mock_instance.reset_mock()
            result = await block.execute({"system": "You are helpful"})
            assert result["assistant"] == "response"
            mock_instance.generate.assert_called_with("You are helpful", "")

            # test with empty input
            mock_instance.reset_mock()
            result = await block.execute({})
            assert result["assistant"] == "response"
            mock_instance.generate.assert_called_with("", "")

    @pytest.mark.asyncio
    async def test_llm_block_execute_only_returns_declared_outputs(self):
        """Test LLMBlock returns only assistant field"""
        block = LLMBlock(model="test-model")

        with patch("lib.blocks.builtin.llm.Generator") as mock_generator:
            mock_instance = mock_generator.return_value
            mock_instance.generate = AsyncMock(return_value="Test response")

            input_data = {
                "system": "You are helpful",
                "user": "Say hello",
                "metadata": {"test": "value"},
                "extra_field": "should not be in output",
            }

            result = await block.execute(input_data)

            # llm block returns assistant, system, and user (rendered templates)
            assert result == {
                "assistant": "Test response",
                "system": "You are helpful",
                "user": "Say hello",
            }
            assert "metadata" not in result
            assert "extra_field" not in result

    def test_llm_block_config_schema(self):
        """Test LLMBlock config schema"""
        block = LLMBlock()
        schema = block.get_schema()

        assert "config_schema" in schema
        config = schema["config_schema"]

        # check JSON schema format
        assert config["type"] == "object"
        assert "properties" in config

        assert "model" in config["properties"]
        assert config["properties"]["model"]["type"] == "string"
        assert config["properties"]["model"]["default"] is None

        assert "temperature" in config["properties"]
        assert config["properties"]["temperature"]["type"] == "number"
        assert config["properties"]["temperature"]["default"] == 0.7

        assert "max_tokens" in config["properties"]
        assert config["properties"]["max_tokens"]["type"] == "integer"
        assert config["properties"]["max_tokens"]["default"] == 2048
