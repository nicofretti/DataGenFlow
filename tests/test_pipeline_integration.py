import pytest

from lib.entities import RecordCreate
from lib.entities import pipeline as pipeline_entities
from lib.workflow import Pipeline as WorkflowPipeline


@pytest.mark.asyncio
async def test_pipeline_execution_with_trace():
    # create a simple pipeline with just llm block
    pipeline_def = {
        "name": "Test Pipeline",
        "blocks": [
            {"type": "TextGenerator", "config": {"temperature": 0.7}},
        ],
    }

    pipeline = WorkflowPipeline.load_from_dict(pipeline_def)

    # execute with test data
    input_data = {"system": "You are a helpful assistant", "user": "Say hello"}

    # mock the llm call to avoid actual api requests
    from unittest.mock import AsyncMock, patch

    with patch("litellm.acompletion", new_callable=AsyncMock) as mock_gen:
        from unittest.mock import MagicMock

        mock_gen.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="Hello! How can I help you today?"))]
        )

        exec_result = await pipeline.execute(input_data)
        assert isinstance(exec_result, pipeline_entities.ExecutionResult)

        # verify result has assistant output
        assert "assistant" in exec_result.result
        assert exec_result.result["assistant"] == "Hello! How can I help you today?"

        # verify trace structure (TraceEntry objects)
        assert len(exec_result.trace) == 1
        assert exec_result.trace[0].block_type == "TextGenerator"

        # verify trace has accumulated_state
        assert exec_result.trace[0].accumulated_state is not None
        assert (
            exec_result.trace[0].accumulated_state["assistant"]
            == "Hello! How can I help you today?"
        )


@pytest.mark.asyncio
async def test_storage_saves_trace(storage):
    # test that trace is saved with record
    # create pipeline first for foreign key
    pipeline_def = {"name": "Test", "blocks": []}
    pipeline_id = await storage.save_pipeline("Test", pipeline_def)

    trace = [
        {
            "block_type": "TextGenerator",
            "input": {"system": "test", "user": "test"},
            "output": {"assistant": "response"},
        }
    ]

    record = RecordCreate(
        output="test assistant",
        metadata={"system": "test system", "user": "test user"},
        trace=trace,
    )

    record_id = await storage.save_record(record, pipeline_id=pipeline_id)

    # retrieve and verify
    saved_record = await storage.get_by_id(record_id)
    assert saved_record is not None
    assert saved_record.trace is not None
    assert len(saved_record.trace) == 1
    assert saved_record.trace[0]["block_type"] == "TextGenerator"


@pytest.mark.asyncio
async def test_storage_handles_none_trace(storage):
    # test that records without trace work fine (None is converted to [])
    record = RecordCreate(
        output="test assistant", metadata={"system": "test system", "user": "test user"}, trace=None
    )

    record_id = await storage.save_record(record)

    # retrieve and verify - validator converts None to []
    saved_record = await storage.get_by_id(record_id)
    assert saved_record is not None
    assert saved_record.trace == []
