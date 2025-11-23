import pytest

from lib.entities import pipeline as pipeline_entities
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
async def test_pipeline_output_includes_assistant():
    # test that assistant output is in result
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

        exec_result = await pipeline.execute({"system": "test", "user": "test"})
        assert isinstance(exec_result, pipeline_entities.ExecutionResult)

        # result should include assistant output
        assert exec_result.result["assistant"] == "Default output"
