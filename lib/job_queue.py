import json
import logging
import threading
import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Any


class JobQueue:
    """in-memory job queue manager with thread-safe operations"""

    def __init__(self) -> None:
        self._jobs: dict[int, dict[str, Any]] = {}  # job_id -> job metadata
        self._active_job: int | None = None  # only one job can run at a time
        self._job_history: dict[int, deque[int]] = defaultdict(
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
                "usage": {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cached_tokens": 0,
                    "start_time": time.time(),
                    "end_time": None,
                },
            }

            self._active_job = job_id
            self._add_to_history(pipeline_id, job_id)

    def get_job(self, job_id: int) -> dict[str, Any] | None:
        """get job metadata by id"""
        with self._lock:
            job = self._jobs.get(job_id)
            return job.copy() if job is not None else None

    def update_job(self, job_id: int, **updates: Any) -> bool:
        """update job metadata"""
        with self._lock:
            if job_id not in self._jobs:
                return False

            job = self._jobs[job_id]

            # parse usage json if present
            if "usage" in updates and isinstance(updates["usage"], str):
                try:
                    parsed_usage = json.loads(updates["usage"])
                    updates["usage"] = parsed_usage

                    logger = logging.getLogger(__name__)
                    logger.info(
                        f"JobQueue: parsed usage for job {job_id}: "
                        f"in={parsed_usage.get('input_tokens')}, "
                        f"out={parsed_usage.get('output_tokens')}, "
                        f"cached={parsed_usage.get('cached_tokens')}"
                    )
                except (json.JSONDecodeError, TypeError) as e:

                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"JobQueue: failed to parse usage for job {job_id}: {e}"
                    )

            job.update(updates)

            # clear active job if terminal status and set completed_at consistently
            status = updates.get("status")
            if status in ["completed", "failed", "cancelled", "stopped"]:
                if self._active_job == job_id:
                    self._active_job = None
                # set completed_at for any terminal status if not already set
                if "completed_at" not in updates:
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

    def delete_job(self, job_id: int) -> bool:
        """remove job from memory completely"""
        with self._lock:
            if job_id not in self._jobs:
                return False

            pipeline_id = self._jobs[job_id]["pipeline_id"]

            # remove from jobs dict
            del self._jobs[job_id]

            # remove from history
            if pipeline_id in self._job_history:
                history = self._job_history[pipeline_id]
                if job_id in history:
                    self._job_history[pipeline_id] = deque(
                        [jid for jid in history if jid != job_id], maxlen=10
                    )

            if self._active_job == job_id:
                self._active_job = None

            return True

    def get_active_job(self) -> dict[str, Any] | None:
        """get currently running job"""
        with self._lock:
            if self._active_job is None:
                return None
            job = self._jobs.get(self._active_job)
            return job.copy() if job is not None else None

    def get_pipeline_history(self, pipeline_id: int) -> list[dict[str, Any]]:
        """get last 10 jobs for a pipeline"""
        with self._lock:
            job_ids = list(self._job_history.get(pipeline_id, []))
            return [self._jobs[jid].copy() for jid in job_ids if jid in self._jobs]

    def _add_to_history(self, pipeline_id: int, job_id: int) -> None:
        """add job to pipeline history (max 10 jobs)"""
        self._job_history[pipeline_id].append(job_id)
