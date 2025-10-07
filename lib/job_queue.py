import threading
from collections import defaultdict, deque
from datetime import datetime
from typing import Dict, List, Optional


class JobQueue:
    """in-memory job queue manager with thread-safe operations"""

    def __init__(self):
        self._jobs: Dict[int, dict] = {}  # job_id -> job metadata
        self._active_job: Optional[int] = None  # only one job can run at a time
        self._job_history: Dict[int, deque] = defaultdict(
            lambda: deque(maxlen=10)
        )  # pipeline_id -> last 10 job_ids
        self._lock = threading.Lock()

    def create_job(
        self, job_id: int, pipeline_id: int, total_seeds: int, status: str = "running"
    ) -> None:
        """register a new job in memory"""
        with self._lock:
            if self._active_job is not None:
                raise RuntimeError(
                    f"Job {self._active_job} is already running. Cancel it first."
                )

            self._jobs[job_id] = {
                "id": job_id,
                "pipeline_id": pipeline_id,
                "status": status,
                "progress": 0.0,
                "current_seed": 0,
                "total_seeds": total_seeds,
                "current_block": None,
                "current_step": None,
                "records_generated": 0,
                "records_failed": 0,
                "error": None,
                "started_at": datetime.now().isoformat(),
                "completed_at": None,
            }

            self._active_job = job_id
            self._add_to_history(pipeline_id, job_id)

    def get_job(self, job_id: int) -> Optional[dict]:
        """get job metadata by id"""
        with self._lock:
            return self._jobs.get(job_id)

    def update_job(self, job_id: int, **updates) -> bool:
        """update job metadata"""
        with self._lock:
            if job_id not in self._jobs:
                return False

            job = self._jobs[job_id]
            job.update(updates)

            # clear active job if completed/failed/cancelled
            if updates.get("status") in ["completed", "failed", "cancelled"]:
                if self._active_job == job_id:
                    self._active_job = None
                if updates.get("status") != "cancelled":
                    job["completed_at"] = datetime.now().isoformat()

            return True

    def cancel_job(self, job_id: int) -> bool:
        """mark job as cancelled"""
        with self._lock:
            if job_id not in self._jobs:
                return False

            self._jobs[job_id]["status"] = "cancelled"
            self._jobs[job_id]["completed_at"] = datetime.now().isoformat()

            if self._active_job == job_id:
                self._active_job = None

            return True

    def get_active_job(self) -> Optional[dict]:
        """get currently running job"""
        with self._lock:
            if self._active_job is None:
                return None
            return self._jobs.get(self._active_job)

    def get_pipeline_history(self, pipeline_id: int) -> List[dict]:
        """get last 10 jobs for a pipeline"""
        with self._lock:
            job_ids = list(self._job_history.get(pipeline_id, []))
            return [self._jobs[jid] for jid in job_ids if jid in self._jobs]

    def _add_to_history(self, pipeline_id: int, job_id: int) -> None:
        """add job to pipeline history (max 10 jobs)"""
        self._job_history[pipeline_id].append(job_id)
