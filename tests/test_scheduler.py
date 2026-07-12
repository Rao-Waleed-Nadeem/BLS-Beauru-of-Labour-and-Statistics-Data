from datetime import datetime, timedelta, timezone

import pytest

from pipeline.scheduler import (
    Job,
    JobQueue,
    JobStatus,
    PrioritySystem,
    TaskScheduler,
)


def test_priority_system_resolves_named_levels():
    priority_system = PrioritySystem(
        {"high_priority": 0, "default_priority": 1, "low_priority": 2}
    )

    assert priority_system.resolve("Critical") == 0
    assert priority_system.resolve("High") == 1
    assert priority_system.resolve("Medium") == 2
    assert priority_system.resolve("Low") == 2
    assert priority_system.resolve(0) == 0


def test_job_queue_orders_by_priority():
    queue = JobQueue()
    low_priority_job = Job(collector="archive_sync", priority=2)
    high_priority_job = Job(collector="rss_sync", priority=0)

    queue.enqueue(low_priority_job)
    queue.enqueue(high_priority_job)

    dispatched = queue.dispatch_next()
    assert dispatched is not None
    assert dispatched.collector == "rss_sync"


def test_job_queue_orders_by_scheduled_time_for_equal_priority():
    queue = JobQueue()
    earlier = datetime(2026, 1, 1, tzinfo=timezone.utc)
    later = datetime(2026, 1, 2, tzinfo=timezone.utc)

    queue.enqueue(Job(collector="later", priority=1, scheduled_time=later))
    queue.enqueue(Job(collector="earlier", priority=1, scheduled_time=earlier))

    dispatched = queue.dispatch_next()
    assert dispatched is not None
    assert dispatched.collector == "earlier"


def test_job_queue_rejects_duplicate_ids():
    queue = JobQueue()
    job = Job(job_id="job-1", collector="rss_sync", priority=0)
    queue.enqueue(job)

    with pytest.raises(ValueError, match="Duplicate job ID"):
        queue.enqueue(Job(job_id="job-1", collector="calendar_sync", priority=1))


def test_job_to_dict_and_from_dict_round_trip():
    job = Job(
        job_id="job-1",
        collector="api",
        program_id="BLS-PROGRAM-001",
        dataset_id="BLS-DATASET-001",
        priority=0,
        status=JobStatus.PENDING,
    )

    restored = Job.from_dict(job.to_dict())

    assert restored.job_id == job.job_id
    assert restored.collector == "api"
    assert restored.program_id == job.program_id
    assert restored.dataset_id == job.dataset_id
    assert restored.priority == 0
    assert restored.status == JobStatus.PENDING


def test_task_scheduler_initializes_with_registry():
    scheduler = TaskScheduler().initialize()

    assert scheduler.registry_cache is not None
    assert len(scheduler.registry_cache.datasets) == 8


def test_task_scheduler_requires_initialization_for_registry_jobs():
    scheduler = TaskScheduler()

    with pytest.raises(RuntimeError, match="must be initialized"):
        scheduler.build_queue_from_registry()


def test_task_scheduler_schedule_sync_jobs_creates_configured_jobs():
    scheduler = TaskScheduler().initialize()
    now = datetime(2026, 7, 12, tzinfo=timezone.utc)

    jobs = scheduler.schedule_sync_jobs(now=now)

    assert len(jobs) == 3
    collectors = {job.collector for job in jobs}
    assert collectors == {"calendar_sync", "archive_sync", "rss_sync"}
    assert scheduler.queue.pending_count() == 3


def test_task_scheduler_schedule_sync_jobs_respects_interval():
    scheduler = TaskScheduler().initialize()
    now = datetime(2026, 7, 12, tzinfo=timezone.utc)

    first_run = scheduler.schedule_sync_jobs(now=now)
    second_run = scheduler.schedule_sync_jobs(now=now + timedelta(minutes=1))

    assert len(first_run) == 3
    assert len(second_run) == 0


def test_task_scheduler_build_queue_from_registry():
    scheduler = TaskScheduler().initialize()
    jobs = scheduler.build_queue_from_registry()

    assert len(jobs) > 0
    assert all(job.program_id for job in jobs)
    assert all(job.dataset_id for job in jobs)
    assert {job.collector for job in jobs}.issubset({"api", "html", "pdf"})


def test_task_scheduler_dispatch_and_complete():
    scheduler = TaskScheduler().initialize()
    scheduler.enqueue_collection_job(
        collector="api",
        program_id="BLS-PROGRAM-001",
        dataset_id="BLS-DATASET-001",
        priority=0,
    )
    scheduler.enqueue_collection_job(
        collector="html",
        program_id="BLS-PROGRAM-002",
        dataset_id="BLS-DATASET-002",
        priority=1,
    )

    dispatched = scheduler.dispatch()
    assert dispatched is not None
    assert dispatched.status == JobStatus.RUNNING
    assert dispatched.collector == "api"

    scheduler.complete_job(dispatched.job_id)
    assert scheduler.queue.get_job(dispatched.job_id).status == JobStatus.COMPLETED

    next_job = scheduler.dispatch()
    assert next_job is not None
    assert next_job.collector == "html"


def test_task_scheduler_fail_job():
    scheduler = TaskScheduler().initialize()
    job = scheduler.enqueue_collection_job(collector="rss_sync", priority=0)
    scheduler.dispatch()

    scheduler.fail_job(job.job_id)

    failed_job = scheduler.queue.get_job(job.job_id)
    assert failed_job is not None
    assert failed_job.status == JobStatus.FAILED


def test_public_scheduler_exports():
    from pipeline import scheduler

    assert scheduler.TaskScheduler is TaskScheduler
    assert scheduler.JobQueue is JobQueue
    assert scheduler.JobStatus is JobStatus
