import pytest

from lib.errors import ValidationError
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

    with pytest.raises(ValidationError, match="returned undeclared fields"):
        await pipeline.execute({})


@pytest.mark.asyncio
async def test_pipeline_output_default_to_assistant():
    # test default pipeline_output when no block sets it
    pipeline_def = {
        "name": "Test",
        "blocks": [{"type": "TextGenerator", "config": {}}],
    }

    pipeline = WorkflowPipeline.load_from_dict(pipeline_def)

    from unittest.mock import AsyncMock, patch

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_gen:
        from unittest.mock import MagicMock

        mock_gen.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Default output"))]
        )

        result, trace, trace_id = await pipeline.execute({"system": "test", "user": "test"})

        # pipeline_output should default to assistant
        assert result["pipeline_output"] == "Default output"
        assert result["assistant"] == "Default output"
