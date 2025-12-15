from lib.entities import JobStatus
from lib.job_queue import JobQueue


def test_update_job_sets_completed_at_and_clears_active():
    q = JobQueue()
    q.create_job(job_id=1, pipeline_id=100, total_seeds=10)

    # active job should be set
    active_job = q.get_active_job()
    assert active_job is not None
    assert active_job.id == 1

    # update via update_job to cancelled should set completed_at and clear active
    q.update_job(1, status=JobStatus.CANCELLED)
    j = q.get_job(1)
    assert j is not None
    assert j.status == JobStatus.CANCELLED
    assert j.completed_at is not None
    assert q.get_active_job() is None


def test_getters_return_shallow_copies():
    q = JobQueue()
    q.create_job(job_id=2, pipeline_id=200, total_seeds=5)

    job_copy = q.get_job(2)
    assert job_copy is not None
    # mutate returned model
    job_copy.status = JobStatus.FAILED

    # internal state should not reflect external mutation
    job_internal = q.get_job(2)
    assert job_internal is not None
    assert job_internal.status == JobStatus.RUNNING


def test_pipeline_history_returns_copies():
    q = JobQueue()
    q.create_job(job_id=3, pipeline_id=300, total_seeds=1)
    # finish job 3
    q.update_job(3, status=JobStatus.COMPLETED)

    q.create_job(job_id=4, pipeline_id=300, total_seeds=1)
    q.update_job(4, status=JobStatus.FAILED)

    history = q.get_pipeline_history(300)
    assert len(history) >= 2

    # mutate the returned history entry
    history[0].status = JobStatus.CANCELLED

    # fetching history again should show original status preserved
    history2 = q.get_pipeline_history(300)
    assert history2[0].status != JobStatus.CANCELLED
