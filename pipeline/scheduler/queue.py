import heapq
from datetime import datetime
from typing import Dict, List, Optional

from pipeline.scheduler.models import Job, JobStatus


class JobQueue:
    """Priority queue for scheduler work items. Lower priority value means higher urgency."""

    def __init__(self) -> None:
        self._heap: List[tuple] = []
        self._jobs: Dict[str, Job] = {}
        self._sequence = 0

    def enqueue(self, job: Job) -> None:
        if job.job_id in self._jobs:
            raise ValueError(f"Duplicate job ID: {job.job_id}")

        self._jobs[job.job_id] = job
        self._push_pending(job)

    def _push_pending(self, job: Job) -> None:
        if job.status != JobStatus.PENDING:
            return

        heapq.heappush(
            self._heap,
            (
                job.priority,
                job.scheduled_time,
                self._sequence,
                job.job_id,
            ),
        )
        self._sequence += 1

    def peek_next(self) -> Optional[Job]:
        self._discard_non_pending_head()
        if not self._heap:
            return None
        return self._jobs[self._heap[0][3]]

    def dispatch_next(self) -> Optional[Job]:
        self._discard_non_pending_head()
        if not self._heap:
            return None

        _, _, _, job_id = heapq.heappop(self._heap)
        job = self._jobs[job_id]
        job.status = JobStatus.RUNNING
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def get_jobs_by_status(self, status: JobStatus) -> List[Job]:
        return [job for job in self._jobs.values() if job.status == status]

    def pending_count(self) -> int:
        return len(self.get_jobs_by_status(JobStatus.PENDING))

    def clear(self) -> None:
        self._heap.clear()
        self._jobs.clear()
        self._sequence = 0

    def _discard_non_pending_head(self) -> None:
        while self._heap:
            job = self._jobs[self._heap[0][3]]
            if job.status == JobStatus.PENDING:
                break
            heapq.heappop(self._heap)
