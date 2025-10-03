"""
Tests for LLMBlock in lib/blocks/llm.py
"""
import pytest
from unittest.mock import AsyncMock, patch

from lib.blocks.llm import LLMBlock


class TestLLMBlock:
    """Test LLM block functionality"""
    
    def test_llm_block_init(self):
        """Test LLMBlock initialization"""
        block = LLMBlock(model="test-model", endpoint="http://test")
        assert block.model == "test-model"
        assert block.endpoint == "http://test"
        
        # test with default values
        block_default = LLMBlock()
        assert block_default.model is not None
        assert block_default.endpoint is not None
    
    def test_llm_block_schema(self):
        """Test LLMBlock schema generation"""
        block = LLMBlock()
        schema = block.get_schema()
        
        assert "type" in schema
        assert schema["type"] == "object"
        assert "properties" in schema
        
        properties = schema["properties"]
        assert "system" in properties
        assert "user" in properties
        
        # check that system and user are required
        assert "required" in schema
        assert "system" in schema["required"]
        assert "user" in schema["required"]
    
    @pytest.mark.asyncio
    async def test_llm_block_execute_success(self):
        """Test LLMBlock execution with mocked LLM response"""
        block = LLMBlock(model="test-model")
        
        # mock the generator to return a test response
        with patch.object(block.generator, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = "This is a test response"
            
            input_data = {
                "system": "You are a helpful assistant",
                "user": "Say hello"
            }
            
            result = await block.execute(input_data)
            
            # check that generator was called with correct parameters
            mock_generate.assert_called_once_with(
                "You are a helpful assistant",
                "Say hello"
            )
            
            # check result
            assert "assistant" in result
            assert result["assistant"] == "This is a test response"
            
            # check that original input is preserved
            assert result["system"] == "You are a helpful assistant"
            assert result["user"] == "Say hello"
    
    @pytest.mark.asyncio
    async def test_llm_block_execute_with_error(self):
        """Test LLMBlock execution when LLM call fails"""
        block = LLMBlock(model="test-model")
        
        # mock the generator to raise an exception
        with patch.object(block.generator, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.side_effect = Exception("LLM API error")
            
            input_data = {
                "system": "You are a helpful assistant",
                "user": "Say hello"
            }
            
            # the block should handle the error gracefully
            with pytest.raises(Exception):
                await block.execute(input_data)
    
    @pytest.mark.asyncio
    async def test_llm_block_execute_missing_required_fields(self):
        """Test LLMBlock execution with missing required fields"""
        block = LLMBlock()
        
        # test with missing system
        with pytest.raises(KeyError):
            await block.execute({"user": "Say hello"})
        
        # test with missing user
        with pytest.raises(KeyError):
            await block.execute({"system": "You are helpful"})
        
        # test with empty input
        with pytest.raises(KeyError):
            await block.execute({})
    
    @pytest.mark.asyncio
    async def test_llm_block_execute_with_additional_fields(self):
        """Test LLMBlock execution with additional input fields"""
        block = LLMBlock(model="test-model")
        
        with patch.object(block.generator, 'generate', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = "Test response"
            
            input_data = {
                "system": "You are helpful",
                "user": "Say hello",
                "metadata": {"test": "value"},
                "extra_field": "should be preserved"
            }
            
            result = await block.execute(input_data)
            
            # check that additional fields are preserved
            assert result["metadata"] == {"test": "value"}
            assert result["extra_field"] == "should be preserved"
            assert result["assistant"] == "Test response"
    
    def test_llm_block_schema_validation(self):
        """Test that LLMBlock schema can validate inputs"""
        block = LLMBlock()
        schema = block.get_schema()
        
        # this would typically be used by a JSON schema validator
        # we'll do basic checks here
        assert "properties" in schema
        assert "system" in schema["properties"]
        assert "user" in schema["properties"]
        
        # check property types
        assert schema["properties"]["system"]["type"] == "string"
        assert schema["properties"]["user"]["type"] == "string"