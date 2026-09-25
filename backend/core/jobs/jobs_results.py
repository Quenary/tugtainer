from __future__ import annotations

from collections.abc import Sequence
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

    @property
    def name(self) -> str:
        return str(self.container.name) if self.container else ""

    @property
    def image(self) -> str:
        if self.image_spec:
            return self.image_spec
        if self.container and self.container.config and self.container.config.image:
            return str(self.container.config.image)
        return ""


@dataclass
class ServiceJobResult:
    service_name: str
    service_image: str
    result: ContainerJobOutcome | None = None
    service_id: str | None = None
    local_digests: list[str] = field(default_factory=list)
    remote_digests: list[str] = field(default_factory=list)
    local_image: ImageInspectResult | None = None
    remote_image: ImageInspectResult | None = None

    @property
    def name(self) -> str:
        return self.service_name

    @property
    def image(self) -> str:
        return self.service_image


JobItemResult = ContainerJobResult | ServiceJobResult


@dataclass
class JobNotificationResult:
    """Jinja notification context; same shape as the previous HostActionResult."""

    host_id: int
    host_name: str
    items: Sequence[JobItemResult] = field(default_factory=list)
    prune_result: str | None = None


def job_to_notification_result(job: Job) -> JobNotificationResult:
    items: list[JobItemResult] = [
        res
        for slot in (job.get("containers") or {}).values()
        if (res := slot.get("result")) is not None
    ]
    return JobNotificationResult(
        host_id=job.get("host_id", 0),
        host_name=job.get("host_name", ""),
        items=items,
        prune_result=job.get("prune_result"),
    )
