"""tests for pipeline constraint enforcement"""

import json
from typing import Any

import pytest

from lib.entities import JobStatus, pipeline
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
        from lib.entities import Job, JobStatus

        job_data = self.jobs.get(job_id)
        if job_data is None:
            return None
        # return Job object instead of dict, providing defaults for required fields
        if isinstance(job_data, dict):
            # ensure all required fields exist with defaults
            defaults = {
                "id": job_id,
                "pipeline_id": 1,
                "status": JobStatus.RUNNING,
                "total_seeds": 1,
                "started_at": "2024-01-01T00:00:00",
            }
            # merge defaults with actual data (actual data takes precedence)
            full_data = {**defaults, **job_data}
            return Job(**full_data)
        return job_data

    def update_job(self, job_id, **updates):
        from lib.entities import JobStatus, Usage

        if job_id not in self.jobs:
            self.jobs[job_id] = {
                "id": job_id,
                "pipeline_id": 1,
                "status": JobStatus.RUNNING,
                "total_seeds": 1,
                "started_at": "2024-01-01T00:00:00",
            }

        # convert usage to dict for storage
        if "usage" in updates:
            usage = updates["usage"]
            if isinstance(usage, Usage):
                updates["usage"] = usage.model_dump()
            elif isinstance(usage, str):
                try:
                    updates["usage"] = json.loads(usage)
                except (json.JSONDecodeError, TypeError):
                    pass

        self.jobs[job_id].update(updates)

    async def update_and_persist(self, job_id, storage, **updates):
        """mock update_and_persist for testing"""
        self.update_job(job_id, **updates)
        return True


class MockStorage:
    """mock storage for testing"""

    def __init__(self):
        self.records = []
        self.pipelines: dict[int, Any] = {}

    async def save_record(self, record, pipeline_id, job_id):
        self.records.append({"record": record, "pipeline_id": pipeline_id, "job_id": job_id})

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
    assert isinstance(results, list)

    # verify that execution stopped before processing all 10 seeds
    assert len(results) < 10, f"Expected < 10 results, got {len(results)}"

    # verify job was marked as stopped
    job = job_queue.get_job(job_id)
    assert job is not None
    assert job.status == JobStatus.STOPPED, f"Expected status STOPPED, got {job.status}"

    # verify usage in job exceeds the constraint
    usage_data = job.usage
    total_tokens = usage_data.input_tokens + usage_data.output_tokens + usage_data.cached_tokens
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
    assert isinstance(results, list)

    # verify all seeds were processed
    assert len(results) == num_seeds, f"Expected {num_seeds} results, got {len(results)}"

    # verify job was NOT marked as stopped
    job = job_queue.get_job(job_id)
    assert job.status != JobStatus.STOPPED


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
    assert isinstance(results, list)

    # verify execution stopped
    assert len(results) < 10

    # verify stopped status
    job = job_queue.get_job(job_id)
    assert job.status == JobStatus.STOPPED


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
    assert isinstance(results, list)

    # verify execution stopped before all seeds
    assert len(results) < 10
    assert job_queue.get_job(job_id).status == JobStatus.STOPPED


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
    assert isinstance(results, list)

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
    assert isinstance(results, list)

    # with 200 tokens already used, should stop after ~1 seed (200 + 170 = 370)
    assert len(results) <= 2, f"Expected <= 2 results with pre-existing usage, got {len(results)}"
    assert job_queue.get_job(job_id).status == JobStatus.STOPPED


# ============================================================================
# normal pipeline constraint tests
# ============================================================================


@pytest.mark.asyncio
async def test_normal_pipeline_stops_at_max_total_tokens():
    """test normal pipeline stops when token constraint exceeded"""
    import tempfile
    from pathlib import Path

    # create pipeline without multiplier (normal pipeline)
    pipeline_obj = object.__new__(Pipeline)
    pipeline_obj.name = "Normal Pipeline"
    pipeline_obj.blocks = []
    pipeline_obj._block_instances = [
        MockBlock(output_tokens=100),  # 170 tokens per seed (50+100+20)
    ]

    # create mock storage with pipeline
    storage = MockStorage()
    storage.pipelines = {
        1: {
            "id": 1,
            "name": "Test Pipeline",
            "definition": {
                "blocks": [{"type": "MockBlock"}],
                "constraints": {"max_total_tokens": 400},  # stop after ~2 seeds
            },
            "created_at": "2025-01-01",
        }
    }

    # create seed file with multiple seeds
    seeds = [{"repetitions": 1, "metadata": {"test": f"seed{i}"}} for i in range(5)]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(seeds, f)
        seed_file = f.name

    try:
        job_queue = MockJobQueue()
        job_id = 1

        # simulate job processor flow
        from lib.entities import PipelineRecord
        from lib.entities import pipeline as pipeline_module

        # load pipeline
        pipeline_data = PipelineRecord(**storage.pipelines[1])
        constraints = pipeline_module.Constraints(**pipeline_data.definition["constraints"])
        accumulated_usage = pipeline_module.Usage()

        # mock save_record to track results
        records_generated = 0

        # process seeds
        for idx, seed in enumerate(seeds):
            metadata: dict[str, Any] = seed.get("metadata", {})  # type: ignore[assignment]

            # execute pipeline
            result = await pipeline_obj.execute(metadata)

            # accumulate usage
            accumulated_usage.input_tokens += result.usage.input_tokens
            accumulated_usage.output_tokens += result.usage.output_tokens
            accumulated_usage.cached_tokens += result.usage.cached_tokens

            records_generated += 1

            # check constraints (normal pipeline path)
            exceeded, constraint_name = constraints.is_exceeded(accumulated_usage)
            if exceeded:
                job_queue.update_job(
                    job_id,
                    status="stopped",
                    error=f"Constraint exceeded: {constraint_name}",
                )
                break

        # verify stopped before processing all seeds
        assert records_generated < len(seeds), (
            f"Expected < {len(seeds)} records, got {records_generated}"
        )

        # verify job marked as stopped
        job = job_queue.get_job(job_id)
        assert job is not None
        assert job.status == JobStatus.STOPPED
        assert "max_total_tokens" in (job.error or "")

        # verify usage exceeds constraint
        assert accumulated_usage.total_tokens >= 400

    finally:
        Path(seed_file).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_normal_pipeline_stops_at_execution_time():
    """test execution time constraint works for normal pipelines"""
    import asyncio
    import tempfile
    from pathlib import Path

    # create slow block
    class SlowBlock:
        outputs = ["result"]

        async def execute(self, data):
            await asyncio.sleep(0.5)  # 500ms per execution
            return {
                "result": "done",
                "_usage": {"input_tokens": 10, "output_tokens": 10, "cached_tokens": 0},
            }

    pipeline_obj = object.__new__(Pipeline)
    pipeline_obj.name = "Slow Pipeline"
    pipeline_obj.blocks = []
    pipeline_obj._block_instances = [SlowBlock()]

    storage = MockStorage()
    storage.pipelines = {
        1: {
            "id": 1,
            "name": "Test Pipeline",
            "definition": {
                "blocks": [{"type": "SlowBlock"}],
                "constraints": {"max_total_execution_time": 1},  # 1 second limit
            },
            "created_at": "2025-01-01",
        }
    }

    seeds = [{"repetitions": 1, "metadata": {"test": f"seed{i}"}} for i in range(5)]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(seeds, f)
        seed_file = f.name

    try:
        job_queue = MockJobQueue()
        job_id = 1

        from lib.entities import PipelineRecord
        from lib.entities import pipeline as pipeline_module

        pipeline_data = PipelineRecord(**storage.pipelines[1])
        constraints = pipeline_module.Constraints(**pipeline_data.definition["constraints"])
        accumulated_usage = pipeline_module.Usage()

        records_generated = 0

        for idx, seed in enumerate(seeds):
            metadata: dict[str, Any] = seed.get("metadata", {})  # type: ignore[assignment]
            result = await pipeline_obj.execute(metadata)

            accumulated_usage.input_tokens += result.usage.input_tokens
            accumulated_usage.output_tokens += result.usage.output_tokens
            accumulated_usage.cached_tokens += result.usage.cached_tokens

            records_generated += 1

            # check constraints
            exceeded, constraint_name = constraints.is_exceeded(accumulated_usage)
            if exceeded:
                job_queue.update_job(
                    job_id,
                    status="stopped",
                    error=f"Constraint exceeded: {constraint_name}",
                )
                break

        # should stop after ~2 executions (1 second / 0.5 seconds per execution)
        assert records_generated < len(seeds)
        assert records_generated <= 3, (
            f"Expected <= 3 records with 1s limit, got {records_generated}"
        )

        job = job_queue.get_job(job_id)
        assert job.status == JobStatus.STOPPED
        assert "max_total_execution_time" in (job.error or "")

    finally:
        Path(seed_file).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_normal_pipeline_cumulative_usage():
    """test usage accumulates correctly across multiple seeds"""
    pipeline_obj = object.__new__(Pipeline)
    pipeline_obj.name = "Normal Pipeline"
    pipeline_obj.blocks = []
    pipeline_obj._block_instances = [MockBlock(output_tokens=100)]

    from lib.entities import PipelineRecord
    from lib.entities import pipeline as pipeline_module

    storage = MockStorage()
    storage.pipelines = {
        1: {
            "id": 1,
            "name": "Test",
            "definition": {
                "blocks": [{"type": "MockBlock"}],
                "constraints": {"max_total_tokens": 500},
            },
            "created_at": "2025-01-01",
        }
    }

    job_queue = MockJobQueue()
    job_id = 1

    pipeline_data = PipelineRecord(**storage.pipelines[1])
    constraints = pipeline_module.Constraints(**pipeline_data.definition["constraints"])

    # start with pre-existing usage
    accumulated_usage = pipeline_module.Usage(
        input_tokens=100, output_tokens=100, cached_tokens=50
    )  # 250 tokens already used

    seeds = [{"metadata": {"test": f"seed{i}"}} for i in range(5)]

    records_generated = 0
    for seed in seeds:
        metadata: dict[str, Any] = seed.get("metadata", {})
        result = await pipeline_obj.execute(metadata)

        accumulated_usage.input_tokens += result.usage.input_tokens
        accumulated_usage.output_tokens += result.usage.output_tokens
        accumulated_usage.cached_tokens += result.usage.cached_tokens

        records_generated += 1

        exceeded, constraint_name = constraints.is_exceeded(accumulated_usage)
        if exceeded:
            job_queue.update_job(job_id, status="stopped")
            break

    # with 250 pre-existing + 170 per seed, should stop after 1-2 seeds
    assert records_generated <= 2, f"Expected <= 2 with pre-existing usage, got {records_generated}"
    assert job_queue.get_job(job_id).status == JobStatus.STOPPED
    assert accumulated_usage.total_tokens >= 500


@pytest.mark.asyncio
async def test_invalid_constraints_continues_execution():
    """test invalid constraints don't crash pipeline"""
    pipeline_obj = object.__new__(Pipeline)
    pipeline_obj.name = "Normal Pipeline"
    pipeline_obj.blocks = []
    pipeline_obj._block_instances = [MockBlock(output_tokens=50)]

    from lib.entities import PipelineRecord
    from lib.entities import pipeline as pipeline_module

    # pipeline with invalid constraints
    pipeline_data = PipelineRecord(
        id=1,
        name="Test",
        definition={
            "blocks": [{"type": "MockBlock"}],
            "constraints": {"invalid_field": "bad_value", "another_bad": 123},
        },
        created_at="2025-01-01",
    )

    # try to load constraints (should handle gracefully)
    try:
        constraints = pipeline_module.Constraints(**pipeline_data.definition["constraints"])
    except (ValueError, KeyError, TypeError):
        # if it fails, use empty constraints (this is the expected behavior)
        constraints = pipeline_module.Constraints()

    # verify execution continues with empty constraints
    result = await pipeline_obj.execute({"test": "data"})

    assert result is not None
    # empty constraints should not restrict execution (-1 = unlimited)
    assert constraints.max_total_tokens == -1
    assert constraints.max_total_execution_time == -1


@pytest.mark.asyncio
async def test_constraint_enforced_at_exact_boundary():
    """test constraint triggers at exact limit (not off-by-one)"""

    # create block that returns exact token amounts
    class ExactBlock:
        outputs = ["result"]

        async def execute(self, data):
            return {
                "result": "test",
                "_usage": {
                    "input_tokens": 100,
                    "output_tokens": 100,
                    "cached_tokens": 0,
                },
            }

    pipeline_obj = object.__new__(Pipeline)
    pipeline_obj.name = "Exact Pipeline"
    pipeline_obj.blocks = []
    pipeline_obj._block_instances = [ExactBlock()]

    from lib.entities import pipeline as pipeline_module

    # set constraint to exact expected value
    constraints = pipeline_module.Constraints(max_total_tokens=600)
    accumulated_usage = pipeline_module.Usage()

    job_queue = MockJobQueue()
    job_id = 1

    records_generated = 0
    max_iterations = 10

    for i in range(max_iterations):
        result = await pipeline_obj.execute({"test": f"seed{i}"})

        accumulated_usage.input_tokens += result.usage.input_tokens
        accumulated_usage.output_tokens += result.usage.output_tokens
        accumulated_usage.cached_tokens += result.usage.cached_tokens

        records_generated += 1

        # check at exact boundary
        exceeded, constraint_name = constraints.is_exceeded(accumulated_usage)
        if exceeded:
            job_queue.update_job(job_id, status="stopped")
            break

    # each iteration: 200 tokens. constraint: 600 tokens
    # should stop after 3 iterations (600 tokens), not before or after
    assert records_generated == 3, (
        f"Expected exactly 3 records at boundary, got {records_generated}"
    )
    assert accumulated_usage.total_tokens == 600
    assert job_queue.get_job(job_id).status == JobStatus.STOPPED
