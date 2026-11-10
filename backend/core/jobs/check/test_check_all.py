import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from backend.core.jobs.check.check_all import check_all_hosts
from backend.core.jobs.jobs_results import ServiceJobResult
from backend.exception import TugAgentClientError
from backend.testing import patch_async_session

base_module = "backend.core.jobs.check.check_all"


def _job(host: SimpleNamespace, kind: str, name: str) -> dict:
    return {
        "kind": kind,
        "host_id": host.id,
        "host_name": host.name,
        "containers": {
            name: {
                "result": ServiceJobResult(
                    service_name=name,
                    service_image="img",
                    result="available",
                )
            }
        },
    }


def _ready(job: dict) -> SimpleNamespace:
    done = asyncio.Event()
    done.set()
    return SimpleNamespace(job=job, error=None, done=done)


def _hosts(mocker: MockerFixture, hosts: list[SimpleNamespace]) -> AsyncMock:
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = hosts
    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)
    patch_async_session(mocker, base_module, session)
    return mocker.patch(f"{base_module}.send_job_notification", AsyncMock())


@pytest.mark.asyncio
@pytest.mark.parametrize("manual", [False, True])
async def test_check_all_hosts_submits_services_only_for_swarm(
    mocker: MockerFixture, manual: bool
):
    plain = SimpleNamespace(id=1, name="plain", is_swarm=False)
    swarm = SimpleNamespace(id=2, name="swarm", is_swarm=True)
    notify = _hosts(mocker, [plain, swarm])
    calls: list[tuple[int, str]] = []

    async def fake_submit(host, kind, **kwargs):
        calls.append((host.id, kind))
        return _ready(_job(host, kind, f"{host.name}-{kind}"))

    mocker.patch(
        f"{base_module}.host_job_coordinator.submit",
        side_effect=fake_submit,
    )

    await check_all_hosts(manual=manual)

    plain_calls = [kind for host_id, kind in calls if host_id == 1]
    swarm_calls = [kind for host_id, kind in calls if host_id == 2]
    assert plain_calls == ["check"]
    assert swarm_calls == ["check", "check_services"]
    results = notify.await_args.args[0]
    by_host = {item.host_id: item for item in results}
    assert set(by_host) == {1, 2}
    assert [item.name for item in by_host[1].items] == ["plain-check"]
    assert [item.name for item in by_host[2].items] == [
        "swarm-check",
        "swarm-check_services",
    ]


@pytest.mark.asyncio
async def test_check_all_hosts_keeps_container_job_when_swarm_is_stale(
    mocker: MockerFixture,
):
    host = SimpleNamespace(id=1, name="swarm", is_swarm=True)
    notify = _hosts(mocker, [host])

    async def fake_submit(submitted, kind, **kwargs):
        if kind == "check_services":
            raise TugAgentClientError(
                "Agent request error", "http://agent", "GET", 503, "not a manager"
            )
        return _ready(_job(submitted, kind, "web"))

    mocker.patch(
        f"{base_module}.host_job_coordinator.submit",
        side_effect=fake_submit,
    )

    await check_all_hosts(manual=False)

    results = notify.await_args.args[0]
    assert len(results) == 1
    assert [item.name for item in results[0].items] == ["web"]


@pytest.mark.asyncio
async def test_check_all_hosts_queues_services_before_container_finishes(
    mocker: MockerFixture,
) -> None:
    host = SimpleNamespace(id=1, name="swarm", is_swarm=True)
    _hosts(mocker, [host])
    services_queued = asyncio.Event()

    async def fake_submit(submitted, kind, **kwargs):
        runtime = SimpleNamespace(
            job=_job(submitted, kind, kind),
            error=None,
            done=asyncio.Event(),
        )
        if kind == "check":

            async def release() -> None:
                await services_queued.wait()
                runtime.done.set()

            _ = asyncio.create_task(release())
            return runtime
        services_queued.set()
        runtime.done.set()
        return runtime

    mocker.patch(
        f"{base_module}.host_job_coordinator.submit",
        side_effect=fake_submit,
    )

    await asyncio.wait_for(check_all_hosts(manual=False), timeout=1)
    assert services_queued.is_set()
