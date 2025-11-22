from unittest.mock import AsyncMock, patch

import pytest

from lib.entities import pipeline as pipeline_entities
from lib.errors import BlockNotFoundError, ValidationError
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
        exec_result = await pipeline.execute({"system": "test", "user": "test"})
        assert isinstance(exec_result, pipeline_entities.ExecutionResult)

        assert exec_result.result["assistant"] == "generated response"
        assert len(exec_result.trace) == 1


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
        exec_result = await pipeline.execute({"system": "test", "user": "test"})
        assert isinstance(exec_result, pipeline_entities.ExecutionResult)

        assert exec_result.result["assistant"] == "hello world"
        assert exec_result.result["valid"] is True
        assert len(exec_result.trace) == 2


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


@pytest.mark.asyncio
async def test_multiplier_block_must_be_first():
    pipeline_def = {
        "name": "Invalid Multiplier Pipeline",
        "blocks": [
            {"type": "TextGenerator", "config": {}},
            {"type": "MarkdownMultiplierBlock", "config": {}},
        ],
    }

    with pytest.raises(ValidationError, match="must be first"):
        Pipeline.load_from_dict(pipeline_def)


@pytest.mark.asyncio
async def test_only_one_multiplier_allowed():
    pipeline_def = {
        "name": "Multiple Multipliers Pipeline",
        "blocks": [
            {"type": "MarkdownMultiplierBlock", "config": {}},
            {"type": "MarkdownMultiplierBlock", "config": {}},
        ],
    }

    with pytest.raises(ValidationError, match="Only one multiplier"):
        Pipeline.load_from_dict(pipeline_def)


@pytest.mark.asyncio
async def test_multiplier_pipeline_execution():
    pipeline_def = {
        "name": "Multiplier Pipeline",
        "blocks": [
            {
                "type": "MarkdownMultiplierBlock",
                "config": {"parser_type": "sentence", "chunk_size": 100, "chunk_overlap": 10},
            },
            {"type": "ValidatorBlock", "config": {"min_length": 1}},
        ],
    }

    pipeline = Pipeline.load_from_dict(pipeline_def)

    markdown_content = "Sentence one. Sentence two. Sentence three."
    results = await pipeline.execute({"file_content": markdown_content})

    assert isinstance(results, list)
    assert len(results) > 0

    for exec_result in results:
        assert isinstance(exec_result, pipeline_entities.ExecutionResult)
        assert "valid" in exec_result.result
        assert isinstance(exec_result.trace, list)
        assert isinstance(exec_result.trace_id, str)
