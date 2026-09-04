import asyncio
from types import SimpleNamespace
from typing import Any, cast

import pytest

from backend.core.jobs.jobs_coordinator import (
    HostJobCoordinator,
    HostJobRuntime,
    merge_or_append_job,
)
from backend.core.jobs.jobs_tracker import HostJobTracker
from backend.enums.job_status_enum import EJobStatus


def test_merge_or_append_same_kind_unstarted() -> None:
    jobs: list[HostJobRuntime] = []
    first = merge_or_append_job(jobs, "check", {"a"}, True)
    second = merge_or_append_job(jobs, "check", {"b"}, True)
    assert first is second
    assert len(jobs) == 1
    assert jobs[0].names == {"a", "b"}
    assert jobs[0].manual is True


def test_merge_or_append_names_none_wins() -> None:
    jobs: list[HostJobRuntime] = []
    merge_or_append_job(jobs, "update", {"a"}, True)
    merge_or_append_job(jobs, "update", None, True)
    assert len(jobs) == 1
    assert jobs[0].names is None


def test_merge_or_append_different_kind_appends() -> None:
    jobs: list[HostJobRuntime] = []
    merge_or_append_job(jobs, "check", {"a"}, True)
    merge_or_append_job(jobs, "update", {"b"}, True)
    assert len(jobs) == 2
    assert jobs[0].kind == "check"
    assert jobs[1].kind == "update"


def test_merge_or_append_started_job_is_not_merged() -> None:
    jobs: list[HostJobRuntime] = []
    first = merge_or_append_job(jobs, "check", {"a"}, True)
    first.started = True
    second = merge_or_append_job(jobs, "check", {"b"}, True)
    assert first is not second
    assert len(jobs) == 2
    assert jobs[0].names == {"a"}
    assert jobs[1].names == {"b"}


@pytest.mark.asyncio
async def test_submit_queues_second_kind_until_first_finishes(mocker) -> None:
    coord = HostJobCoordinator()
    host = cast(Any, SimpleNamespace(id=1, name="h"))
    started = mocker.Mock()
    release_check = mocker.AsyncMock()
    check_order: list[str] = []

    async def slow_check(*args, **kwargs):
        check_order.append("check-start")
        started()
        await release_check()
        check_order.append("check-end")
        return True

    async def fast_update(*args, **kwargs):
        check_order.append("update")
        return True

    mocker.patch(
        "backend.core.jobs.check.check_host.run_check_host_job",
        side_effect=slow_check,
    )
    mocker.patch(
        "backend.core.jobs.update.update_host.run_update_host_job",
        side_effect=fast_update,
    )
    mocker.patch(
        "backend.core.jobs.jobs_coordinator.AgentClientManager.get_host_client",
        return_value=mocker.Mock(),
    )
    mocker.patch(
        "backend.core.jobs.jobs_tracker.HostJobTracker.begin",
        return_value=None,
    )
    mocker.patch(
        "backend.core.jobs.jobs_tracker.HostJobTracker.finish",
        return_value={"kind": "check"},
    )
    mocker.patch(
        "backend.core.jobs.jobs_tracker.HostJobTracker.complete_current",
        return_value={"kind": "check"},
    )
    mocker.patch(
        "backend.core.jobs.jobs_tracker.HostJobTracker.set_queued",
        return_value=None,
    )
    mocker.patch(
        "backend.core.jobs.jobs_tracker.HostJobTracker.set_status",
        return_value=None,
    )

    wait_event = asyncio.Event()
    go_event = asyncio.Event()

    async def wait_then_go():
        wait_event.set()
        await go_event.wait()

    release_check.side_effect = wait_then_go

    check_job = await coord.submit(host, "check", names=["a"], manual=True, wait=False)
    await wait_event.wait()
    update_job = await coord.submit(
        host, "update", names=["b"], manual=True, wait=False
    )
    assert check_job.started is True
    assert update_job.started is False
    go_event.set()
    await check_job.done.wait()
    await update_job.done.wait()
    assert check_order == ["check-start", "check-end", "update"]


@pytest.mark.asyncio
async def test_sequential_jobs_accumulate_completed(mocker) -> None:
    coord = HostJobCoordinator()
    host = cast(Any, SimpleNamespace(id=99013, name="completed-host"))

    async def check(*args, **kwargs):
        return True

    async def update(*args, **kwargs):
        return True

    mocker.patch(
        "backend.core.jobs.check.check_host.run_check_host_job",
        side_effect=check,
    )
    mocker.patch(
        "backend.core.jobs.update.update_host.run_update_host_job",
        side_effect=update,
    )
    mocker.patch(
        "backend.core.jobs.jobs_coordinator.AgentClientManager.get_host_client",
        return_value=mocker.Mock(),
    )

    check_job = await coord.submit(
        host, "check", names=["a", "b"], manual=True, wait=False
    )
    update_job = await coord.submit(
        host, "update", names=["c", "d"], manual=True, wait=False
    )
    await check_job.done.wait()
    await update_job.done.wait()

    state = HostJobTracker(host).get()
    assert state is not None
    assert state["status"] == EJobStatus.DONE
    assert state["current"] is None
    assert len(state["completed"]) == 2
    assert state["completed"][0]["kind"] == "check"
    assert state["completed"][0]["names"] == ["a", "b"]
    assert state["completed"][1]["kind"] == "update"
    assert state["completed"][1]["names"] == ["c", "d"]
