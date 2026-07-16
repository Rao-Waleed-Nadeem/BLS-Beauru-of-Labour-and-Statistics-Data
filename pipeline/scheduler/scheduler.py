from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from BLS.pipeline.config.loader import ConfigLoader
from BLS.pipeline.registry.cache import RegistryCache
from BLS.pipeline.registry.loader import RegistryLoader
from .models import Job, JobStatus
from .priority import PrioritySystem
from .queue import JobQueue


class TaskScheduler:
    """
    Creates and dispatches collection work items.

    The scheduler never downloads data; it only manages the job queue.
    """

    def __init__(
        self,
        config_loader: Optional[ConfigLoader] = None,
        registry_loader: Optional[RegistryLoader] = None,
    ) -> None:
        self.config_loader = config_loader or ConfigLoader()
        self.registry_loader = registry_loader or RegistryLoader()
        self._scheduler_config = self.config_loader.load_scheduler()["scheduler"]
        self.priority_system = PrioritySystem(self._scheduler_config["queues"])
        self.queue = JobQueue()
        self.registry_cache: Optional[RegistryCache] = None
        self._last_sync: Dict[str, datetime] = {}

    def initialize(self) -> "TaskScheduler":
        self.registry_cache = self.registry_loader.get_cache()
        return self

    def _ensure_initialized(self) -> RegistryCache:
        if self.registry_cache is None:
            raise RuntimeError("Scheduler must be initialized before scheduling jobs.")
        return self.registry_cache

    def enqueue(self, job: Job) -> Job:
        self.queue.enqueue(job)
        return job

    def enqueue_collection_job(
        self,
        collector: str,
        program_id: str = "",
        dataset_id: str = "",
        series_id: str = "",
        source_url: str = "",
        priority: Optional[int] = None,
        scheduled_time: Optional[datetime] = None,
    ) -> Job:
        job = Job(
            collector=collector,
            program_id=program_id,
            dataset_id=dataset_id,
            series_id=series_id,
            source_url=source_url,
            priority=(
                priority
                if priority is not None
                else self.priority_system.default_priority
            ),
            scheduled_time=scheduled_time or datetime.now(timezone.utc),
        )
        return self.enqueue(job)

    def schedule_sync_jobs(self, now: Optional[datetime] = None) -> List[Job]:
        current_time = now or datetime.now(timezone.utc)
        created_jobs: List[Job] = []

        for job_name, job_config in self._scheduler_config["jobs"].items():
            interval = timedelta(minutes=job_config["interval_minutes"])
            last_run = self._last_sync.get(job_name)

            if last_run is None or current_time - last_run >= interval:
                job = self.enqueue_collection_job(
                    collector=job_name,
                    priority=self.priority_system.resolve(job_config["priority"]),
                    scheduled_time=current_time,
                )
                self._last_sync[job_name] = current_time
                created_jobs.append(job)

        return created_jobs

    def build_queue_from_registry(self) -> List[Job]:
        registry = self._ensure_initialized()
        created_jobs: List[Job] = []

        for dataset in registry.datasets.values():
            for method in dataset.collection_methods:
                job = self.enqueue_collection_job(
                    collector=method.lower(),
                    program_id=dataset.program_id,
                    dataset_id=dataset.dataset_id,
                    priority=self.priority_system.default_priority,
                )
                created_jobs.append(job)

        return created_jobs

    def dispatch(self) -> Optional[Job]:
        return self.queue.dispatch_next()

    def complete_job(self, job_id: str) -> Job:
        job = self._get_existing_job(job_id)
        job.status = JobStatus.COMPLETED
        return job

    def fail_job(self, job_id: str) -> Job:
        job = self._get_existing_job(job_id)
        job.status = JobStatus.FAILED
        return job

    def get_pending_jobs(self) -> List[Job]:
        return self.queue.get_jobs_by_status(JobStatus.PENDING)

    def _get_existing_job(self, job_id: str) -> Job:
        job = self.queue.get_job(job_id)
        if job is None:
            raise ValueError(f"Job not found: {job_id}")
        return job
