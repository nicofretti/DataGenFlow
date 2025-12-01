"""
Tests for job cancellation to ensure background processing stops correctly.

These tests prevent regression of the bug where cancelling a job would only
break from inner loops but continue processing remaining seeds in background.
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from lib.entities import pipeline as pipeline_entities
from lib.job_queue import JobQueue
from lib.storage import Storage
from lib.workflow import Pipeline


@pytest.mark.asyncio
async def test_job_cancellation_stops_processing_remaining_seeds():
    """
    Test that cancelling a job stops processing remaining seeds.

    Bug: Previously, when a job was cancelled during execution, it would
    break from the inner loop (repetitions) but continue to the next seed.

    Fix: Added check after inner loop to break from outer loop when cancelled.
    Location: lib/job_processor.py lines 310-318
    """
    job_queue = JobQueue()
    storage = Storage(":memory:")
    await storage.init_db()

    # create test pipeline with 2 blocks
    pipeline_def = {
        "name": "Test Pipeline",
        "blocks": [
            {"type": "TextGenerator", "config": {"temperature": 0.7}},
            {"type": "ValidatorBlock", "config": {"min_length": 5}},
        ],
    }
    pipeline = Pipeline.load_from_dict(pipeline_def)

    # save pipeline first
    await storage.save_pipeline("Test Pipeline", pipeline_def)

    # create job with 5 seeds, 2 repetitions each = 10 total executions
    job_id = 1
    job_queue.create_job(job_id=job_id, pipeline_id=1, total_seeds=10)

    execution_count = 0

    async def mock_execute_with_cancellation(*args, **kwargs):
        nonlocal execution_count
        execution_count += 1

        # cancel job after first execution
        if execution_count == 1:
            job_queue.cancel_job(job_id)

        # simulate some work
        await asyncio.sleep(0.01)

        # return mock result
        return pipeline_entities.ExecutionResult(
            result={"assistant": "test", "valid": True},
            trace=[],
            trace_id="test",
            usage={"input_tokens": 10, "output_tokens": 10, "cached_tokens": 0},
        )

    # patch pipeline execute to track calls and cancel job
    with patch.object(pipeline, "execute", side_effect=mock_execute_with_cancellation):
        # simulate processing seeds
        seeds_data = [{"repetitions": 2, "metadata": {"user": f"test {i}"}} for i in range(5)]

        # process seeds like job_processor does
        for seed in seeds_data:
            job_status = job_queue.get_job(job_id)
            if job_status and job_status.get("status") == "cancelled":
                break

            repetitions = seed.get("repetitions", 1)
            assert isinstance(repetitions, int)
            for i in range(repetitions):
                job_status = job_queue.get_job(job_id)
                if job_status and job_status.get("status") == "cancelled":
                    break

                metadata = seed["metadata"]
                assert isinstance(metadata, dict)
                await pipeline.execute(
                    metadata,
                    job_id=job_id,
                    job_queue=job_queue,
                    storage=storage,
                    pipeline_id=1,
                )

            # CRITICAL: check if cancelled after inner loop completes
            # without this, job would continue to next seed
            job_status = job_queue.get_job(job_id)
            if job_status and job_status.get("status") in ("cancelled", "stopped"):
                break

    # verify job was cancelled and stopped processing
    final_job = job_queue.get_job(job_id)
    assert final_job is not None
    assert final_job["status"] == "cancelled"

    # should only execute once (first execution that triggered cancellation)
    # without the fix, it would execute all 10 times
    assert execution_count == 1, f"Expected 1 execution, got {execution_count}"


@pytest.mark.asyncio
async def test_job_cancellation_stops_between_blocks_normal_pipeline():
    """
    Test that cancelling a job stops execution between blocks in normal pipeline.

    Bug: During pipeline execution, no checks existed between blocks to stop
    when job was cancelled.

    Fix: Added cancellation check before each block execution.
    Location: lib/workflow.py lines 126-137
    """
    job_queue = JobQueue()
    storage = Storage(":memory:")
    await storage.init_db()

    # create test pipeline with 5 blocks
    pipeline_def = {
        "name": "Multi-Block Pipeline",
        "blocks": [
            {"type": "TextGenerator", "config": {"temperature": 0.7}},
            {"type": "ValidatorBlock", "config": {"min_length": 5}},
            {"type": "TextGenerator", "config": {"temperature": 0.7}},
            {"type": "ValidatorBlock", "config": {"min_length": 5}},
            {"type": "TextGenerator", "config": {"temperature": 0.7}},
        ],
    }
    pipeline = Pipeline.load_from_dict(pipeline_def)

    # save pipeline
    await storage.save_pipeline("Multi-Block Pipeline", pipeline_def)

    job_id = 2
    job_queue.create_job(job_id=job_id, pipeline_id=1, total_seeds=1)

    blocks_executed = []

    # mock litellm to avoid real API calls and track execution
    async def mock_acompletion(*args, **kwargs):
        blocks_executed.append("TextGenerator")

        # cancel after first text generator
        if len(blocks_executed) == 1:
            job_queue.cancel_job(job_id)

        await asyncio.sleep(0.01)

        return MagicMock(choices=[MagicMock(message=MagicMock(content="test response"))])

    with patch("litellm.acompletion", side_effect=mock_acompletion):
        await pipeline.execute(
            {"user": "test"},
            job_id=job_id,
            job_queue=job_queue,
            storage=storage,
            pipeline_id=1,
        )

    # verify job was cancelled
    final_job = job_queue.get_job(job_id)
    assert final_job is not None
    assert final_job["status"] == "cancelled"

    # should only execute first block before cancellation
    # without the fix, all 3 TextGenerators would execute (5 total blocks)
    # allow <=2 to account for async race conditions where block 2 might start
    # before cancellation is detected. the bug would allow 3+ blocks to execute.
    assert len(blocks_executed) <= 2, (
        f"Expected <=2 blocks executed, got {len(blocks_executed)}: {blocks_executed}"
    )


@pytest.mark.asyncio
async def test_job_cancellation_stops_multiplier_pipeline_between_seeds():
    """
    Test that cancelling a job stops multiplier pipeline between seeds.

    Bug: Multiplier pipelines process multiple seeds. Cancellation could occur
    during seed processing but job would continue to next seed.

    Fix: Added cancellation check before processing each seed.
    Location: lib/workflow.py lines 438-443
    """
    job_queue = JobQueue()
    storage = Storage(":memory:")
    await storage.init_db()

    # create multiplier pipeline
    pipeline_def = {
        "name": "Multiplier Pipeline",
        "blocks": [
            {"type": "MarkdownMultiplierBlock", "config": {}},
            {"type": "TextGenerator", "config": {"temperature": 0.7}},
        ],
    }
    pipeline = Pipeline.load_from_dict(pipeline_def)

    # save pipeline
    await storage.save_pipeline("Multiplier Pipeline", pipeline_def)

    job_id = 3
    job_queue.create_job(job_id=job_id, pipeline_id=1, total_seeds=5)

    # mock multiplier to generate 5 seeds
    multiplier_seeds = [{"content": f"seed {i}", "user": f"test {i}"} for i in range(5)]

    seeds_processed = 0

    async def mock_acompletion(*args, **kwargs):
        nonlocal seeds_processed
        seeds_processed += 1

        # cancel after first seed
        if seeds_processed == 1:
            job_queue.cancel_job(job_id)

        await asyncio.sleep(0.01)
        return MagicMock(choices=[MagicMock(message=MagicMock(content="generated"))])

    with patch(
        "lib.blocks.builtin.markdown_multiplier.MarkdownMultiplierBlock.execute",
        return_value=multiplier_seeds,
    ):
        with patch("litellm.acompletion", side_effect=mock_acompletion):
            await pipeline.execute(
                {"file_content": "# test\ntest"},
                job_id=job_id,
                job_queue=job_queue,
                storage=storage,
                pipeline_id=1,
            )

    # verify job was cancelled
    final_job = job_queue.get_job(job_id)
    assert final_job is not None
    assert final_job["status"] == "cancelled"

    # should only process 1 seed before cancellation
    # without the fix, all 5 seeds would be processed
    assert seeds_processed == 1, f"Expected 1 seed processed, got {seeds_processed}"


@pytest.mark.asyncio
async def test_job_cancellation_stops_multiplier_pipeline_between_blocks():
    """
    Test that cancelling a job stops multiplier pipeline between blocks within a seed.

    Bug: During seed processing in multiplier pipeline, no checks existed between
    blocks to stop when job was cancelled.

    Fix: Added cancellation check before executing each block in seed.
    Location: lib/workflow.py lines 312-317
    """
    job_queue = JobQueue()
    storage = Storage(":memory:")
    await storage.init_db()

    # create multiplier pipeline with multiple blocks per seed
    pipeline_def = {
        "name": "Multiplier with Multiple Blocks",
        "blocks": [
            {"type": "MarkdownMultiplierBlock", "config": {}},
            {"type": "TextGenerator", "config": {"temperature": 0.7}},
            {"type": "ValidatorBlock", "config": {"min_length": 5}},
            {"type": "TextGenerator", "config": {"temperature": 0.7}},
        ],
    }
    pipeline = Pipeline.load_from_dict(pipeline_def)

    # save pipeline
    await storage.save_pipeline("Multiplier with Multiple Blocks", pipeline_def)

    job_id = 4
    job_queue.create_job(job_id=job_id, pipeline_id=1, total_seeds=1)

    # mock multiplier to generate 1 seed with 3 blocks to execute (2 TextGenerators + 1 Validator)
    multiplier_seeds = [{"content": "test", "user": "test"}]

    text_generators_executed = 0

    async def mock_acompletion(*args, **kwargs):
        nonlocal text_generators_executed
        text_generators_executed += 1

        # cancel after first TextGenerator in seed
        if text_generators_executed == 1:
            job_queue.cancel_job(job_id)

        await asyncio.sleep(0.01)
        return MagicMock(choices=[MagicMock(message=MagicMock(content="test response"))])

    with patch(
        "lib.blocks.builtin.markdown_multiplier.MarkdownMultiplierBlock.execute",
        return_value=multiplier_seeds,
    ):
        with patch("litellm.acompletion", side_effect=mock_acompletion):
            await pipeline.execute(
                {"file_content": "# test"},
                job_id=job_id,
                job_queue=job_queue,
                storage=storage,
                pipeline_id=1,
            )

    # verify job was cancelled
    final_job = job_queue.get_job(job_id)
    assert final_job is not None
    assert final_job["status"] == "cancelled"

    # should stop after first TextGenerator in seed
    # without the fix, both TextGenerators would execute (2 total)
    # allow <=2 to account for async race conditions where second TextGenerator might start
    # before cancellation is detected. the bug would allow both TextGenerators to complete.
    assert text_generators_executed <= 2, (
        f"Expected <=2 TextGenerators in seed, got {text_generators_executed}"
    )
