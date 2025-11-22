"""tests for pipeline constraint enforcement"""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from lib.entities import pipeline
from lib.workflow import Pipeline


class MockBlock:
    """mock block for testing"""

    def __init__(self, output_tokens=100):
        self.outputs = ["result"]
        self.output_tokens = output_tokens

    async def execute(self, data):
        return {
            "result": "test output",
            "_usage": {
                "input_tokens": 50,
                "output_tokens": self.output_tokens,
                "cached_tokens": 20,
            },
        }


class MockMultiplierBlock:
    """mock multiplier block that generates seeds"""

    def __init__(self, num_seeds=5):
        self.is_multiplier = True
        self.num_seeds = num_seeds
        self.outputs = []

    async def execute(self, data):
        # generate multiple seeds
        return [{"seed": i, "content": f"seed {i}"} for i in range(self.num_seeds)]


class MockJobQueue:
    """mock job queue for testing"""

    def __init__(self):
        self.jobs = {}

    def get_job(self, job_id):
        return self.jobs.get(job_id)

    def update_job(self, job_id, **updates):
        if job_id not in self.jobs:
            self.jobs[job_id] = {}

        # parse usage json if present (mimics real job_queue behavior)
        if "usage" in updates and isinstance(updates["usage"], str):
            try:
                updates["usage"] = json.loads(updates["usage"])
            except (json.JSONDecodeError, TypeError):
                pass

        self.jobs[job_id].update(updates)


class MockStorage:
    """mock storage for testing"""

    def __init__(self):
        self.records = []

    async def save_record(self, record, pipeline_id, job_id):
        self.records.append(
            {"record": record, "pipeline_id": pipeline_id, "job_id": job_id}
        )

    async def update_job(self, job_id, **updates):
        pass


@pytest.mark.asyncio
async def test_multiplier_pipeline_stops_at_max_total_tokens():
    """test that multiplier pipeline stops when max_total_tokens is exceeded"""
    # create pipeline object without initializing blocks
    pipeline_obj = object.__new__(Pipeline)
    pipeline_obj.name = "Test Pipeline"
    pipeline_obj.blocks = []

    # inject mock blocks directly
    pipeline_obj._block_instances = [
        MockMultiplierBlock(num_seeds=10),  # will generate 10 seeds
        MockBlock(output_tokens=100),  # each seed uses ~170 tokens (50+100+20)
    ]

    # set constraint to stop after ~3 seeds (170 tokens per seed * 3 = 510)
    constraints = pipeline.Constraints(max_total_tokens=500)

    # initialize mock job queue with usage tracking
    job_queue = MockJobQueue()
    job_id = 1
    job_queue.jobs[job_id] = {
        "usage": {
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_tokens": 0,
            "start_time": 1234567890.0,
            "end_time": None,
        },
        "records_generated": 0,
    }

    storage = MockStorage()

    # execute pipeline
    results = await pipeline_obj.execute(
        {"file_content": "test"},
        job_id=job_id,
        job_queue=job_queue,
        storage=storage,
        pipeline_id=1,
        constraints=constraints,
    )

    # verify that execution stopped before processing all 10 seeds
    assert len(results) < 10, f"Expected < 10 results, got {len(results)}"

    # verify job was marked as stopped
    job = job_queue.get_job(job_id)
    assert job is not None
    assert job.get("status") == "stopped", f"Expected status 'stopped', got {job.get('status')}"

    # verify usage in job exceeds the constraint
    usage_data = job.get("usage")
    if isinstance(usage_data, str):
        usage_data = json.loads(usage_data)
    total_tokens = (
        usage_data.get("input_tokens", 0)
        + usage_data.get("output_tokens", 0)
        + usage_data.get("cached_tokens", 0)
    )
    assert total_tokens >= 500, f"Expected total_tokens >= 500, got {total_tokens}"


@pytest.mark.asyncio
async def test_multiplier_pipeline_completes_without_constraints():
    """test that multiplier pipeline processes all seeds when no constraints"""
    # create pipeline object without initializing blocks
    pipeline_obj = object.__new__(Pipeline)
    pipeline_obj.name = "Test Pipeline"
    pipeline_obj.blocks = []

    # inject mock blocks directly
    num_seeds = 5
    pipeline_obj._block_instances = [
        MockMultiplierBlock(num_seeds=num_seeds),
        MockBlock(output_tokens=100),
    ]

    # no constraints (empty Constraints object)
    constraints = pipeline.Constraints()

    # initialize mock job queue
    job_queue = MockJobQueue()
    job_id = 1
    job_queue.jobs[job_id] = {
        "usage": {
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_tokens": 0,
            "start_time": 1234567890.0,
            "end_time": None,
        },
        "records_generated": 0,
    }

    storage = MockStorage()

    # execute pipeline
    results = await pipeline_obj.execute(
        {"file_content": "test"},
        job_id=job_id,
        job_queue=job_queue,
        storage=storage,
        pipeline_id=1,
        constraints=constraints,
    )

    # verify all seeds were processed
    assert len(results) == num_seeds, f"Expected {num_seeds} results, got {len(results)}"

    # verify job was NOT marked as stopped
    job = job_queue.get_job(job_id)
    assert job.get("status") != "stopped"


@pytest.mark.asyncio
async def test_multiplier_pipeline_with_max_total_input_tokens():
    """test constraint on input tokens specifically"""
    # create pipeline object without initializing blocks
    pipeline_obj = object.__new__(Pipeline)
    pipeline_obj.name = "Test Pipeline"
    pipeline_obj.blocks = []

    pipeline_obj._block_instances = [
        MockMultiplierBlock(num_seeds=10),
        MockBlock(output_tokens=100),  # uses 50 input tokens per seed
    ]

    # constraint on input tokens only (should stop after ~4 seeds: 50*4=200)
    constraints = pipeline.Constraints(max_total_input_tokens=200)

    job_queue = MockJobQueue()
    job_id = 1
    job_queue.jobs[job_id] = {
        "usage": {
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_tokens": 0,
            "start_time": 1234567890.0,
            "end_time": None,
        },
        "records_generated": 0,
    }

    storage = MockStorage()

    results = await pipeline_obj.execute(
        {"file_content": "test"},
        job_id=job_id,
        job_queue=job_queue,
        storage=storage,
        pipeline_id=1,
        constraints=constraints,
    )

    # verify execution stopped
    assert len(results) < 10

    # verify stopped status
    job = job_queue.get_job(job_id)
    assert job.get("status") == "stopped"


@pytest.mark.asyncio
async def test_multiplier_pipeline_with_max_total_output_tokens():
    """test constraint on output tokens specifically"""
    # create pipeline object without initializing blocks
    pipeline_obj = object.__new__(Pipeline)
    pipeline_obj.name = "Test Pipeline"
    pipeline_obj.blocks = []

    pipeline_obj._block_instances = [
        MockMultiplierBlock(num_seeds=10),
        MockBlock(output_tokens=100),  # uses 100 output tokens per seed
    ]

    # constraint on output tokens only (should stop after ~3 seeds: 100*3=300)
    constraints = pipeline.Constraints(max_total_output_tokens=300)

    job_queue = MockJobQueue()
    job_id = 1
    job_queue.jobs[job_id] = {
        "usage": {
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_tokens": 0,
            "start_time": 1234567890.0,
            "end_time": None,
        },
        "records_generated": 0,
    }

    storage = MockStorage()

    results = await pipeline_obj.execute(
        {"file_content": "test"},
        job_id=job_id,
        job_queue=job_queue,
        storage=storage,
        pipeline_id=1,
        constraints=constraints,
    )

    # verify execution stopped before all seeds
    assert len(results) < 10
    assert job_queue.get_job(job_id).get("status") == "stopped"


@pytest.mark.asyncio
async def test_empty_constraints_allows_unlimited_execution():
    """test that empty Constraints() object doesn't restrict execution"""
    # create pipeline object without initializing blocks
    pipeline_obj = object.__new__(Pipeline)
    pipeline_obj.name = "Test Pipeline"
    pipeline_obj.blocks = []

    num_seeds = 3
    pipeline_obj._block_instances = [
        MockMultiplierBlock(num_seeds=num_seeds),
        MockBlock(output_tokens=10000),  # large token usage
    ]

    # empty constraints should not restrict
    constraints = pipeline.Constraints()

    job_queue = MockJobQueue()
    job_id = 1
    job_queue.jobs[job_id] = {
        "usage": {
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_tokens": 0,
            "start_time": 1234567890.0,
            "end_time": None,
        },
        "records_generated": 0,
    }

    storage = MockStorage()

    results = await pipeline_obj.execute(
        {"file_content": "test"},
        job_id=job_id,
        job_queue=job_queue,
        storage=storage,
        pipeline_id=1,
        constraints=constraints,
    )

    # should process all seeds despite high token usage
    assert len(results) == num_seeds


@pytest.mark.asyncio
async def test_constraint_checking_uses_cumulative_usage():
    """test that constraints check cumulative usage across all seeds"""
    # create pipeline object without initializing blocks
    pipeline_obj = object.__new__(Pipeline)
    pipeline_obj.name = "Test Pipeline"
    pipeline_obj.blocks = []

    pipeline_obj._block_instances = [
        MockMultiplierBlock(num_seeds=5),
        MockBlock(output_tokens=100),  # 170 tokens per seed
    ]

    # set tight constraint
    constraints = pipeline.Constraints(max_total_tokens=400)

    job_queue = MockJobQueue()
    job_id = 1
    # start with some existing usage
    job_queue.jobs[job_id] = {
        "usage": {
            "input_tokens": 100,  # already consumed
            "output_tokens": 100,  # already consumed
            "cached_tokens": 0,
            "start_time": 1234567890.0,
            "end_time": None,
        },
        "records_generated": 0,
    }

    storage = MockStorage()

    results = await pipeline_obj.execute(
        {"file_content": "test"},
        job_id=job_id,
        job_queue=job_queue,
        storage=storage,
        pipeline_id=1,
        constraints=constraints,
    )

    # with 200 tokens already used, should stop after ~1 seed (200 + 170 = 370)
    assert len(results) <= 2, f"Expected <= 2 results with pre-existing usage, got {len(results)}"
    assert job_queue.get_job(job_id).get("status") == "stopped"
