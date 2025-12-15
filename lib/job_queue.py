import threading
from collections import defaultdict, deque
from datetime import datetime
from typing import TYPE_CHECKING, Any

from lib.entities import TERMINAL_STATUSES, Job, JobStatus

if TYPE_CHECKING:
    from lib.storage import Storage


class JobQueue:
    """in-memory job queue manager with thread-safe operations"""

    def __init__(self) -> None:
        self._jobs: dict[int, Job] = {}  # job_id -> Job model
        self._active_job: int | None = None  # only one job can run at a time
        self._job_history: dict[int, deque[int]] = defaultdict(
            lambda: deque(maxlen=10)
        )  # pipeline_id -> last 10 job_ids
        self._lock = threading.Lock()

    def create_job(
        self,
        job_id: int,
        pipeline_id: int,
        total_seeds: int,
        status: JobStatus = JobStatus.RUNNING,
    ) -> None:
        """register a new job in memory"""
        with self._lock:
            if self._active_job is not None:
                raise RuntimeError(f"Job {self._active_job} is already running. Cancel it first.")

            self._jobs[job_id] = Job(
                id=job_id,
                pipeline_id=pipeline_id,
                status=status,
                total_seeds=total_seeds,
                started_at=datetime.now().isoformat(),
            )
            self._active_job = job_id
            self._add_to_history(pipeline_id, job_id)

    def get_job(self, job_id: int) -> Job | None:
        """get job metadata by id"""
        with self._lock:
            job = self._jobs.get(job_id)
            return job.model_copy() if job is not None else None

    def update_job(self, job_id: int, **updates: Any) -> bool:
        """update job metadata"""
        with self._lock:
            if job_id not in self._jobs:
                return False

            job = self._jobs[job_id]

            # pydantic validator handles usage conversion (dict/str/Usage → Usage)
            for key, value in updates.items():
                if hasattr(job, key):
                    setattr(job, key, value)

            # handle terminal status
            status = updates.get("status")
            if status in TERMINAL_STATUSES:
                if self._active_job == job_id:
                    self._active_job = None
                if not updates.get("completed_at"):
                    job.completed_at = datetime.now().isoformat()

            return True

    def cancel_job(self, job_id: int) -> bool:
        """mark job as cancelled"""
        with self._lock:
            if job_id not in self._jobs:
                return False

            job = self._jobs[job_id]
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.now().isoformat()

            if self._active_job == job_id:
                self._active_job = None
            return True

    def delete_job(self, job_id: int) -> bool:
        """remove job from memory completely"""
        with self._lock:
            if job_id not in self._jobs:
                return False

            pipeline_id = self._jobs[job_id].pipeline_id

            del self._jobs[job_id]

            if pipeline_id in self._job_history:
                history = self._job_history[pipeline_id]
                if job_id in history:
                    self._job_history[pipeline_id] = deque(
                        [jid for jid in history if jid != job_id], maxlen=10
                    )

            if self._active_job == job_id:
                self._active_job = None

            return True

    def get_active_job(self) -> Job | None:
        """get currently running job"""
        with self._lock:
            if self._active_job is None:
                return None
            job = self._jobs.get(self._active_job)
            return job.model_copy() if job is not None else None

    def get_pipeline_history(self, pipeline_id: int) -> list[Job]:
        """get last 10 jobs for a pipeline"""
        with self._lock:
            job_ids = list(self._job_history.get(pipeline_id, []))
            return [self._jobs[jid].model_copy() for jid in job_ids if jid in self._jobs]

    def _add_to_history(self, pipeline_id: int, job_id: int) -> None:
        """add job to pipeline history (max 10 jobs)"""
        self._job_history[pipeline_id].append(job_id)

    async def update_and_persist(self, job_id: int, storage: "Storage", **updates: Any) -> bool:
        """update job in both memory and database"""
        if not self.update_job(job_id, **updates):
            return False
        await storage.update_job(job_id, **updates)
        return True
