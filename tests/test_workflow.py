import pytest

from lib.workflow import Pipeline
from lib.errors import BlockNotFoundError


@pytest.mark.asyncio
async def test_pipeline_single_block():
    pipeline_def = {
        "name": "Simple Transform",
        "blocks": [{"type": "TransformerBlock", "config": {"operation": "lowercase"}}],
    }

    pipeline = Pipeline.load_from_dict(pipeline_def)
    result, trace, trace_id = await pipeline.execute({"text": "HELLO WORLD"})

    assert result["text"] == "hello world"
    assert len(trace) == 1


@pytest.mark.asyncio
async def test_pipeline_multiple_blocks():
    pipeline_def = {
        "name": "Transform and Validate",
        "blocks": [
            {"type": "TransformerBlock", "config": {"operation": "strip"}},
            {"type": "ValidatorBlock", "config": {"min_length": 5}},
        ],
    }

    pipeline = Pipeline.load_from_dict(pipeline_def)
    result, trace, trace_id = await pipeline.execute({"text": "  hello world  "})

    assert result["text"] == "hello world"
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
        "blocks": [{"type": "TransformerBlock", "config": {"operation": "lowercase"}}],
    }

    pipeline = Pipeline.load_from_dict(pipeline_def)
    serialized = pipeline.to_dict()

    assert serialized["name"] == "Test Pipeline"
    assert len(serialized["blocks"]) == 1
    assert serialized["blocks"][0]["type"] == "TransformerBlock"
