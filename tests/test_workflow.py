from unittest.mock import AsyncMock, patch

import pytest

from lib.errors import BlockNotFoundError
from lib.workflow import Pipeline


@pytest.mark.asyncio
async def test_pipeline_single_block():
    pipeline_def = {
        "name": "Simple Generation",
        "blocks": [{"type": "TextGenerator", "config": {"temperature": 0.7}}],
    }

    pipeline = Pipeline.load_from_dict(pipeline_def)

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_gen:
        from unittest.mock import MagicMock

        mock_gen.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="generated response"))]
        )
        result, trace, trace_id = await pipeline.execute({"system": "test", "user": "test"})

        assert result["assistant"] == "generated response"
        assert len(trace) == 1


@pytest.mark.asyncio
async def test_pipeline_multiple_blocks():
    pipeline_def = {
        "name": "Generate and Validate",
        "blocks": [
            {"type": "TextGenerator", "config": {"temperature": 0.7}},
            {"type": "ValidatorBlock", "config": {"min_length": 5}},
        ],
    }

    pipeline = Pipeline.load_from_dict(pipeline_def)

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_gen:
        from unittest.mock import MagicMock

        mock_gen.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="hello world"))]
        )
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
        "blocks": [{"type": "TextGenerator", "config": {"temperature": 0.7}}],
    }

    pipeline = Pipeline.load_from_dict(pipeline_def)
    serialized = pipeline.to_dict()

    assert serialized["name"] == "Test Pipeline"
    assert len(serialized["blocks"]) == 1
    assert serialized["blocks"][0]["type"] == "TextGenerator"
