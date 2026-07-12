import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    VALIDATED = "validated"
    ARCHIVED = "archived"
    FAILED = "failed"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Job:
    collector: str
    program_id: str = ""
    dataset_id: str = ""
    series_id: str = ""
    source_url: str = ""
    priority: int = 1
    scheduled_time: datetime = field(default_factory=_utc_now)
    status: JobStatus = JobStatus.PENDING
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "collector": self.collector,
            "program_id": self.program_id,
            "dataset_id": self.dataset_id,
            "series_id": self.series_id,
            "source_url": self.source_url,
            "priority": self.priority,
            "scheduled_time": self.scheduled_time.isoformat(),
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Job":
        scheduled_time = data.get("scheduled_time")
        if isinstance(scheduled_time, str):
            scheduled_time = datetime.fromisoformat(scheduled_time)
        elif scheduled_time is None:
            scheduled_time = _utc_now()

        status_value = data.get("status", JobStatus.PENDING.value)
        status = (
            status_value
            if isinstance(status_value, JobStatus)
            else JobStatus(status_value)
        )

        return cls(
            job_id=data.get("job_id", str(uuid.uuid4())),
            collector=data["collector"],
            program_id=data.get("program_id", ""),
            dataset_id=data.get("dataset_id", ""),
            series_id=data.get("series_id", ""),
            source_url=data.get("source_url", ""),
            priority=data.get("priority", 1),
            scheduled_time=scheduled_time,
            status=status,
        )
