import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from backend.core.jobs.jobs_results import ServiceJobResult
from backend.core.jobs.update.update_all import update_all_hosts
from backend.exception import TugAgentClientError
from backend.testing import patch_async_session

base_module = "backend.core.jobs.update.update_all"


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
                    result="updated",
                )
            }
        },
        "prune_result": "pruned" if kind == "update" else None,
    }


@pytest.fixture
def mock_hosts(mocker: MockerFixture):
    host1 = SimpleNamespace(id=1, name="host1", is_swarm=False)
    host2 = SimpleNamespace(id=2, name="host2", is_swarm=False)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [host1, host2]

    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)

    patch_async_session(mocker, base_module, session)
    mocker.patch(f"{base_module}.send_job_notification", AsyncMock())

    return [host1, host2]


@pytest.mark.asyncio
@pytest.mark.parametrize("manual", [False, True])
async def test_update_all_hosts_submits_each_host(
    mocker: MockerFixture,
    mock_hosts: list[SimpleNamespace],
    manual: bool,
):
    mock_submit = mocker.patch(
        f"{base_module}.host_job_coordinator.submit",
        AsyncMock(
            side_effect=lambda host, kind, **_kwargs: _ready(_job(host, kind, "web"))
        ),
    )

    await update_all_hosts(manual=manual)

    assert mock_submit.call_count == 2
    for host in mock_hosts:
        mock_submit.assert_any_call(
            host,
            "update",
            names=None,
            manual=manual,
            wait=False,
        )


@pytest.mark.asyncio
async def test_update_all_hosts_handles_host_failure(
    mocker: MockerFixture, mock_hosts: list[SimpleNamespace]
):
    async def fake_submit(host, *args, **kwargs):
        if host.id == 1:
            raise RuntimeError("Agent down")
        return _ready(_job(host, "update", "web"))

    mocker.patch(
        f"{base_module}.host_job_coordinator.submit",
        side_effect=fake_submit,
    )
    mock_notify = mocker.patch(
        f"{base_module}.send_job_notification",
        AsyncMock(),
    )

    # Should not raise exception
    await update_all_hosts(manual=True)

    assert mock_notify.call_count == 1
    call_args = mock_notify.call_args[0][0]
    assert len(call_args) == 1


def _ready(job: dict) -> SimpleNamespace:
    done = asyncio.Event()
    done.set()
    return SimpleNamespace(job=job, error=None, done=done)


def _one_host(mocker: MockerFixture, host: SimpleNamespace) -> AsyncMock:
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [host]
    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)
    patch_async_session(mocker, base_module, session)
    return mocker.patch(f"{base_module}.send_job_notification", AsyncMock())


@pytest.mark.asyncio
@pytest.mark.parametrize("manual", [False, True])
async def test_update_all_hosts_submits_services_on_swarm(
    mocker: MockerFixture, manual: bool
):
    host = SimpleNamespace(id=1, name="swarm", is_swarm=True)
    notify = _one_host(mocker, host)
    calls: list[tuple[str, dict]] = []

    async def fake_submit(submitted, kind, **kwargs):
        calls.append((kind, kwargs))
        return _ready(_job(submitted, kind, kind))

    mocker.patch(
        f"{base_module}.host_job_coordinator.submit",
        side_effect=fake_submit,
    )

    await update_all_hosts(manual=manual)

    assert [kind for kind, _kwargs in calls] == ["update", "update_services"]
    assert calls[1][1]["names"] is None
    assert calls[1][1]["manual"] is manual
    assert calls[0][1]["wait"] is False
    assert calls[1][1]["wait"] is False
    assert calls[1][1]["require_available"] is manual
    results = notify.await_args.args[0]
    assert len(results) == 1
    assert results[0].host_id == host.id
    assert [item.name for item in results[0].items] == ["update", "update_services"]
    assert results[0].prune_result == "pruned"


@pytest.mark.asyncio
async def test_update_all_hosts_keeps_container_job_when_swarm_is_stale(
    mocker: MockerFixture,
):
    host = SimpleNamespace(id=1, name="swarm", is_swarm=True)
    notify = _one_host(mocker, host)

    async def fake_submit(submitted, kind, **kwargs):
        if kind == "update_services":
            raise TugAgentClientError(
                "Agent request error", "http://agent", "POST", 503, "not a manager"
            )
        return _ready(_job(submitted, kind, "web"))

    mocker.patch(
        f"{base_module}.host_job_coordinator.submit",
        side_effect=fake_submit,
    )

    await update_all_hosts(manual=True)

    results = notify.await_args.args[0]
    assert len(results) == 1
    assert [item.name for item in results[0].items] == ["web"]


@pytest.mark.asyncio
async def test_update_all_hosts_queues_services_before_container_finishes(
    mocker: MockerFixture,
) -> None:
    host = SimpleNamespace(id=1, name="swarm", is_swarm=True)
    _one_host(mocker, host)
    services_queued = asyncio.Event()

    async def fake_submit(submitted, kind, **kwargs):
        runtime = SimpleNamespace(
            job=_job(submitted, kind, kind),
            error=None,
            done=asyncio.Event(),
        )
        if kind == "update":

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

    await asyncio.wait_for(update_all_hosts(manual=True), timeout=1)
    assert services_queued.is_set()
