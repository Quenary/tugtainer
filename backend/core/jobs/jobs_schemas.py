from typing import Literal, TypedDict

from backend.core.jobs.jobs_results import JobItemResult
from backend.enums.job_status_enum import EJobStatus

JobKind = Literal["check", "update", "check_services", "update_services"]


class JobBase(TypedDict, total=False):
    kind: JobKind
    names: list[str] | None
    status: EJobStatus


class ContainerJob(TypedDict, total=False):
    """Slot of a single container or service inside a job."""

    status: EJobStatus
    result: JobItemResult | None


class Job(JobBase, total=False):
    """One check/update unit of work."""

    host_id: int
    host_name: str
    containers: dict[str, ContainerJob]
    prune_result: str | None
    log: list[str]


class HostState(TypedDict, total=False):
    """Per-host source of truth: current, queued, and completed jobs."""

    status: EJobStatus
    current: Job | None
    queued: list[Job]
    completed: list[Job]
