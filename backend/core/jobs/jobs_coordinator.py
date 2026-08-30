import asyncio
import logging
from dataclasses import dataclass, field

from backend.core.agent_client import AgentClientManager
from backend.core.jobs.jobs_schemas import Job, JobKind
from backend.core.jobs.jobs_tracker import HostJobTracker
from backend.enums.job_status_enum import EJobStatus
from backend.modules.hosts.hosts_model import HostsModel

logger = logging.getLogger("host_job_coordinator")


@dataclass
class HostJobRuntime:
    """In-memory queue unit; not written to the cache."""

    kind: JobKind
    names: set[str] | None
    manual: bool
    done: asyncio.Event = field(default_factory=asyncio.Event)
    job: Job | None = None
    error: BaseException | None = None
    started: bool = False


def _preview_job(runtime: HostJobRuntime) -> Job:
    return {
        "kind": runtime.kind,
        "names": None if runtime.names is None else sorted(runtime.names),
    }


def merge_or_append_job(
    jobs: list[HostJobRuntime],
    kind: JobKind,
    names: set[str] | None,
    manual: bool,
) -> HostJobRuntime:
    """
    Merge into the last unstarted job when it has the same kind.
    Consecutive same-kind requests are batched; a started job is left alone.
    """
    if jobs:
        last = jobs[-1]
        if not last.started and last.kind == kind:
            if last.names is None or names is None:
                last.names = None
            else:
                last.names |= names
            last.manual = last.manual or manual
            return last
    runtime = HostJobRuntime(kind=kind, names=names, manual=manual)
    jobs.append(runtime)
    return runtime


class HostJobCoordinator:
    """Serializes check/update work per host and exposes a mergeable job queue."""

    def __init__(self) -> None:
        self._queues: dict[int, list[HostJobRuntime]] = {}
        self._workers: dict[int, asyncio.Task[None]] = {}
        self._locks: dict[int, asyncio.Lock] = {}

    def _lock(self, host_id: int) -> asyncio.Lock:
        if host_id not in self._locks:
            self._locks[host_id] = asyncio.Lock()
        return self._locks[host_id]

    def reset(self) -> None:
        """Drop in-memory queues (tests). Does not cancel running work."""
        self._queues.clear()
        self._workers.clear()
        self._locks.clear()

    async def submit(
        self,
        host: HostsModel,
        kind: JobKind,
        *,
        names: list[str] | None = None,
        manual: bool = False,
        wait: bool = False,
    ) -> HostJobRuntime:
        names_set: set[str] | None = None if names is None else set(names)
        async with self._lock(host.id):
            jobs = self._queues.setdefault(host.id, [])
            runtime = merge_or_append_job(jobs, kind, names_set, manual)
            pending = [j for j in jobs if not j.started]
            started = next((j for j in jobs if j.started and not j.done.is_set()), None)
            if started:
                HostJobTracker(host).set_queued([_preview_job(j) for j in pending])
            self._ensure_worker(host)

        if wait:
            await runtime.done.wait()
            if runtime.error:
                raise runtime.error
        return runtime

    async def _record_job_end(
        self,
        host: HostsModel,
        tracker: HostJobTracker,
        status: EJobStatus,
    ) -> Job:
        async with self._lock(host.id):
            more = any(j for j in self._queues.get(host.id, []) if not j.started)
        if more:
            return tracker.complete_current(status)
        return tracker.finish(status)

    def _ensure_worker(self, host: HostsModel) -> None:
        existing = self._workers.get(host.id)
        if existing and not existing.done():
            return
        self._workers[host.id] = asyncio.create_task(
            self._run(host),
            name=f"host-job-{host.id}",
        )

    async def _run(self, host: HostsModel) -> None:
        from backend.core.jobs.check.check_host import run_check_host_job
        from backend.core.jobs.update.update_host import run_update_host_job

        tracker = HostJobTracker(host)
        client = AgentClientManager.get_host_client(host)
        try:
            while True:
                async with self._lock(host.id):
                    jobs = self._queues.get(host.id, [])
                    pending = [j for j in jobs if not j.started]
                    if not pending:
                        self._queues[host.id] = []
                        return
                    runtime = pending[0]
                    runtime.started = True
                    queued = [_preview_job(j) for j in pending[1:]]

                names_list = None if runtime.names is None else sorted(runtime.names)
                tracker.begin(runtime.kind, names_list, queued)
                try:
                    if runtime.kind == "check":
                        ok = await run_check_host_job(
                            host,
                            client,
                            manual=runtime.manual if runtime.names is None else True,
                            names=names_list,
                            tracker=tracker,
                        )
                    else:
                        ok = await run_update_host_job(
                            host,
                            client,
                            manual=runtime.manual if runtime.names is None else True,
                            names=names_list,
                            tracker=tracker,
                        )
                    runtime.job = await self._record_job_end(
                        host,
                        tracker,
                        EJobStatus.DONE if ok else EJobStatus.ERROR,
                    )
                except Exception as e:
                    logger.exception(
                        "Host job failed for %s (%s)", host.name, runtime.kind
                    )
                    runtime.error = e
                    runtime.job = await self._record_job_end(
                        host, tracker, EJobStatus.ERROR
                    )
                finally:
                    runtime.done.set()
        finally:
            current = self._workers.get(host.id)
            if current is asyncio.current_task():
                self._workers.pop(host.id, None)


host_job_coordinator = HostJobCoordinator()
