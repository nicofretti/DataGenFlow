import pytest

from lib.workflow import Pipeline as WorkflowPipeline
from models import Record


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

        result, trace, trace_id = await pipeline.execute(input_data)

        # verify result has assistant output
        assert "assistant" in result
        assert result["assistant"] == "Hello! How can I help you today?"

        # verify trace structure
        assert len(trace) == 1
        assert trace[0]["block_type"] == "TextGenerator"

        # verify trace has accumulated_state
        assert "accumulated_state" in trace[0]
        assert trace[0]["accumulated_state"]["assistant"] == "Hello! How can I help you today?"


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

    record = Record(
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
    # test that records without trace work fine
    record = Record(
        output="test assistant", metadata={"system": "test system", "user": "test user"}, trace=None
    )

    record_id = await storage.save_record(record)

    # retrieve and verify
    saved_record = await storage.get_by_id(record_id)
    assert saved_record is not None
    assert saved_record.trace is None
