from unittest.mock import AsyncMock, patch

import pytest

from lib.errors import BlockNotFoundError
from lib.workflow import Pipeline


@pytest.mark.asyncio
async def test_pipeline_single_block():
    pipeline_def = {
        "name": "Simple Generation",
        "blocks": [{"type": "LLMBlock", "config": {"temperature": 0.7}}],
    }

    pipeline = Pipeline.load_from_dict(pipeline_def)

    with patch("lib.generator.Generator.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "generated response"
        result, trace, trace_id = await pipeline.execute({"system": "test", "user": "test"})

        assert result["assistant"] == "generated response"
        assert len(trace) == 1


@pytest.mark.asyncio
async def test_pipeline_multiple_blocks():
    pipeline_def = {
        "name": "Generate and Validate",
        "blocks": [
            {"type": "LLMBlock", "config": {"temperature": 0.7}},
            {"type": "ValidatorBlock", "config": {"min_length": 5}},
        ],
    }

    pipeline = Pipeline.load_from_dict(pipeline_def)

    with patch("lib.generator.Generator.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "hello world"
        result, trace, trace_id = await pipeline.execute({"system": "test", "user": "test"})

        assert result["assistant"] == "hello world"
        assert result["valid"] is True
        assert len(trace) == 2


@pytest.mark.asyncio
async def test_pipeline_invalid_block():
    pipeline_def = {
        "name": "Invalid Pipeline",
        "blocks": [{"type": "NonExistentBlock", "config": {}}],
    }

    with pytest.raises(BlockNotFoundError, match="not found"):
        Pipeline.load_from_dict(pipeline_def)


@pytest.mark.asyncio
async def test_pipeline_to_dict():
    pipeline_def = {
        "name": "Test Pipeline",
        "blocks": [{"type": "LLMBlock", "config": {"temperature": 0.7}}],
    }

    pipeline = Pipeline.load_from_dict(pipeline_def)
    serialized = pipeline.to_dict()

    assert serialized["name"] == "Test Pipeline"
    assert len(serialized["blocks"]) == 1
    assert serialized["blocks"][0]["type"] == "LLMBlock"
