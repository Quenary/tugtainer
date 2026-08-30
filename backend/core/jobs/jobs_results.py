from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from python_on_whales.components.image.models import (
    ImageInspectResult,
)

if TYPE_CHECKING:
    from backend.core.jobs.jobs_schemas import Job

ContainerJobOutcome = Literal[
    "not_available",
    "available",
    "available(notified)",
    "updated",
    "rolled_back",
    "failed",
    None,
]


@dataclass
class ContainerJobResult:
    container: ContainerInspectResult
    result: ContainerJobOutcome | None = None
    image_spec: str | None = None
    local_image: ImageInspectResult | None = None
    remote_image: ImageInspectResult | None = None
    local_digests: list[str] = field(default_factory=list)
    remote_digests: list[str] = field(default_factory=list)
    previous_image_digests: list[str] = field(default_factory=list)
    previous_image_tags: list[str] = field(default_factory=list)
    previous_image_version: str | None = None


@dataclass
class JobNotificationResult:
    """Jinja notification context; same shape as the previous HostActionResult."""

    host_id: int
    host_name: str
    items: list[ContainerJobResult] = field(default_factory=list)
    prune_result: str | None = None


def job_to_notification_result(job: Job) -> JobNotificationResult:
    items = [
        slot["result"]
        for slot in (job.get("containers") or {}).values()
        if slot.get("result") is not None
    ]
    return JobNotificationResult(
        host_id=job["host_id"],
        host_name=job["host_name"],
        items=items,
        prune_result=job.get("prune_result"),
    )
