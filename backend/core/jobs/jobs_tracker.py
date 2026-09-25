import asyncio
from typing import Final, cast

from backend.core.jobs.jobs_cache import JobStateCache
from backend.core.jobs.jobs_results import JobItemResult
from backend.core.jobs.jobs_schemas import (
    ContainerJob,
    HostState,
    Job,
    JobKind,
)
from backend.core.jobs.jobs_util import get_host_cache_key
from backend.core.socket_manager import socket_manager
from backend.enums.job_status_enum import EJobStatus
from backend.modules.hosts.hosts_model import HostsModel

JOB_LOG_MAX_LINES = 500


class HostJobTracker:
    """Read/write helper for the unified per-host job state cache."""

    def __init__(self, host: HostsModel) -> None:
        self._host: Final[HostsModel] = host
        self._cache: Final[JobStateCache[HostState]] = JobStateCache[HostState](
            get_host_cache_key(host)
        )
        self._broadcast_task: asyncio.Task[None] | None = None
        self._pending_broadcast: bool = False

    async def _broadcast_loop(self) -> None:
        while self._pending_broadcast:
            self._pending_broadcast = False
            state = self._cache.get()
            if state:
                await socket_manager.emit(
                    "job_progress", {"host_id": self._host.id, "state": state}
                )
            await asyncio.sleep(0.34)

    def _broadcast(self) -> None:
        self._pending_broadcast = True

        if self._broadcast_task and not self._broadcast_task.done():
            return

        try:
            loop = asyncio.get_running_loop()
            self._broadcast_task = loop.create_task(self._broadcast_loop())
        except RuntimeError:
            pass

    def get(self) -> HostState | None:
        return self._cache.get()

    def begin(
        self,
        kind: JobKind,
        names: list[str] | None,
        queued: list[Job],
    ) -> None:
        existing = self._cache.get() or {}
        containers: dict[str, ContainerJob] = {}
        if names:
            for name in names:
                containers[name] = {"status": EJobStatus.PREPARING}
        current: Job = {
            "kind": kind,
            "names": names,
            "status": EJobStatus.PREPARING,
            "host_id": self._host.id,
            "host_name": self._host.name,
            "containers": containers,
            "log": [],
        }
        self._cache.set(
            {
                "status": EJobStatus.PREPARING,
                "current": current,
                "queued": queued,
                "completed": list(existing.get("completed") or []),
            }
        )
        self._broadcast()

    def set_status(self, status: EJobStatus) -> None:
        state = self._cache.get() or {}
        current = dict(state.get("current") or {})
        if current:
            current["status"] = status
            self._cache.update({"status": status, "current": cast(Job, current)})
        else:
            self._cache.update({"status": status})
        self._broadcast()

    def set_queued(self, queued: list[Job]) -> None:
        self._cache.update({"queued": queued})
        self._broadcast()

    def set_container(
        self,
        name: str,
        status: EJobStatus,
        result: JobItemResult | None = None,
    ) -> None:
        state = self._cache.get() or {}
        current = cast(Job, dict(state.get("current") or {}))
        containers = dict(current.get("containers") or {})
        slot = cast(ContainerJob, dict(containers.get(name) or {}))
        slot["status"] = status
        if result is not None:
            slot["result"] = result
        containers[name] = slot
        current["containers"] = containers
        self._cache.update({"current": cast(Job, current)})
        self._broadcast()

    def append_log(self, line: str) -> None:
        state = self._cache.get() or {}
        current = cast(Job, dict(state.get("current") or {}))
        if not current:
            return
        log = list(current.get("log") or [])
        log.append(line)
        if len(log) > JOB_LOG_MAX_LINES:
            log = log[-JOB_LOG_MAX_LINES:]
        current["log"] = log
        self._cache.update({"current": cast(Job, current)})
        self._broadcast()

    def set_prune_result(self, prune_result: str | None) -> None:
        state = self._cache.get() or {}
        current = dict(state.get("current") or {})
        current["prune_result"] = prune_result
        self._cache.update({"current": cast(Job, current)})
        self._broadcast()

    def complete_current(self, status: EJobStatus) -> Job:
        """Append the current job to completed without marking the host idle."""
        return self._snapshot_current(status, idle=False)

    def finish(self, status: EJobStatus) -> Job:
        return self._snapshot_current(status, idle=True)

    def _snapshot_current(self, status: EJobStatus, *, idle: bool) -> Job:
        state = self._cache.get() or {}
        current = cast(Job, dict(state.get("current") or {}))
        current["status"] = status
        completed = list(state.get("completed") or [])
        completed.append(current)
        data: HostState = {"completed": completed}
        if idle:
            data["status"] = status
            data["current"] = None
            data["queued"] = []
        else:
            data["current"] = current
        self._cache.update(data)
        self._broadcast()
        return current
