import pytest

from lib.workflow import Pipeline as WorkflowPipeline


@pytest.mark.asyncio
async def test_pipeline_output_validation():
    # test that blocks must return declared outputs
    from lib.blocks.base import BaseBlock

    class BadBlock(BaseBlock):
        name = "Bad Block"
        inputs = []
        outputs = ["valid_field"]

        async def execute(self, data):
            # returns undeclared field
            return {"valid_field": "ok", "invalid_field": "bad"}

    pipeline = WorkflowPipeline("Test", [])
    pipeline._block_instances = [BadBlock()]

    with pytest.raises(RuntimeError, match="returned undeclared fields"):
        await pipeline.execute({})


@pytest.mark.asyncio
async def test_pipeline_output_with_formatter():
    # test formatter block sets pipeline_output
    pipeline_def = {
        "name": "Formatted Pipeline",
        "blocks": [
            {"type": "LLMBlock", "config": {}},
            {
                "type": "FormatterBlock",
                "config": {"format_template": "Response: {assistant}"},
            },
        ],
    }

    pipeline = WorkflowPipeline.load_from_dict(pipeline_def)

    from unittest.mock import AsyncMock, patch

    with patch("lib.generator.Generator.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "Hello"

        result, trace = await pipeline.execute({"system": "test", "user": "test"})

        # pipeline_output should be from formatter (last one wins)
        assert result["pipeline_output"] == "Response: Hello"
        assert (
            trace[-1]["accumulated_state"]["pipeline_output"] == "Response: Hello"
        )


@pytest.mark.asyncio
async def test_pipeline_output_default_to_assistant():
    # test default pipeline_output when no block sets it
    pipeline_def = {
        "name": "Test",
        "blocks": [{"type": "LLMBlock", "config": {}}],
    }

    pipeline = WorkflowPipeline.load_from_dict(pipeline_def)

    from unittest.mock import AsyncMock, patch

    with patch("lib.generator.Generator.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "Default output"

        result, trace = await pipeline.execute({"system": "test", "user": "test"})

        # pipeline_output should default to assistant
        assert result["pipeline_output"] == "Default output"
        assert result["assistant"] == "Default output"
