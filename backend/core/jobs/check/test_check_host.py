from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from backend.const import TUGTAINER_HIDDEN_LABEL
from backend.core.jobs.check.check_host import run_check_host_job
from backend.testing import patch_async_session
from shared.runtime.runtime_models import (
    ContainerConfig,
    ContainerInspectResult,
)

SWARM_LABELS = {
    "com.docker.swarm.service.id": "svc-id",
    "com.docker.swarm.service.name": "web",
}

base_module = "backend.core.jobs.check.check_host"


def _container(name: str) -> MagicMock:
    c = MagicMock()
    c.name = name
    return c


@pytest.mark.asyncio
async def test_run_check_host_job_filters_by_names(mocker: MockerFixture):
    host = SimpleNamespace(id=1, name="host")
    client = MagicMock()
    a = _container("a")
    b = _container("b")
    c = _container("c")
    client.container.list = AsyncMock(return_value=[a, b, c])

    session = MagicMock()
    patch_async_session(mocker, base_module, session)
    mocker.patch(f"{base_module}.get_host_containers", AsyncMock(return_value=[]))

    called: list[str] = []

    async def check_one(_client, _host, container, tracker=None):
        called.append(container.name)
        return SimpleNamespace(container=container)

    mocker.patch(f"{base_module}.run_check_container_job", side_effect=check_one)
    tracker = MagicMock()

    ok = await run_check_host_job(
        host,  # type: ignore[arg-type]
        client,
        names=["c", "a"],
        tracker=tracker,
    )

    assert ok is True
    assert called == ["a", "c"]
    tracker.set_status.assert_called()


@pytest.mark.asyncio
async def test_run_check_host_job_skips_hidden(mocker: MockerFixture):
    host = SimpleNamespace(id=1, name="host")
    client = MagicMock()
    visible = ContainerInspectResult(id="a", name="visible")
    hidden = ContainerInspectResult(
        id="b",
        name="hidden",
        config=ContainerConfig(labels={TUGTAINER_HIDDEN_LABEL: "true"}),
    )
    client.container.list = AsyncMock(return_value=[visible, hidden])

    session = MagicMock()
    patch_async_session(mocker, base_module, session)
    mocker.patch(f"{base_module}.get_host_containers", AsyncMock(return_value=[]))

    called: list[str] = []

    async def check_one(_client, _host, container, tracker=None):
        called.append(container.name)

    mocker.patch(f"{base_module}.run_check_container_job", side_effect=check_one)

    ok = await run_check_host_job(
        host,  # type: ignore[arg-type]
        client,
        manual=True,
    )

    assert ok is True
    assert called == ["visible"]


@pytest.mark.asyncio
async def test_run_check_host_job_skips_swarm_tasks_without_names(
    mocker: MockerFixture,
):
    host = SimpleNamespace(id=1, name="host")
    client = MagicMock()
    plain = ContainerInspectResult(id="a", name="plain")
    task = ContainerInspectResult(
        id="b",
        name="web.1.abc",
        config=ContainerConfig(labels=SWARM_LABELS),
    )
    labeled = ContainerInspectResult(
        id="c",
        name="labeled.1.abc",
        config=ContainerConfig(
            labels={**SWARM_LABELS, "dev.quenary.tugtainer.auto_check": "true"}
        ),
    )
    client.container.list = AsyncMock(return_value=[plain, task, labeled])

    patch_async_session(mocker, base_module, MagicMock())
    mocker.patch(f"{base_module}.get_host_containers", AsyncMock(return_value=[]))
    called: list[str] = []

    async def check_one(_client, _host, container, tracker=None):
        called.append(container.name)

    mocker.patch(f"{base_module}.run_check_container_job", side_effect=check_one)

    ok = await run_check_host_job(
        host,  # type: ignore[arg-type]
        client,
        manual=True,
    )

    assert ok is True
    assert called == ["plain"]

    called.clear()
    ok = await run_check_host_job(
        host,  # type: ignore[arg-type]
        client,
        manual=False,
    )

    assert ok is True
    assert called == []


@pytest.mark.asyncio
async def test_run_check_host_job_named_check_keeps_swarm_task(
    mocker: MockerFixture,
):
    host = SimpleNamespace(id=1, name="host")
    client = MagicMock()
    task = ContainerInspectResult(
        id="b",
        name="web.1.abc",
        config=ContainerConfig(labels=SWARM_LABELS),
    )
    client.container.list = AsyncMock(return_value=[task])
    patch_async_session(mocker, base_module, MagicMock())
    mocker.patch(f"{base_module}.get_host_containers", AsyncMock(return_value=[]))
    called: list[str] = []

    async def check_one(_client, _host, container, tracker=None):
        called.append(container.name)

    mocker.patch(f"{base_module}.run_check_container_job", side_effect=check_one)

    ok = await run_check_host_job(
        host,  # type: ignore[arg-type]
        client,
        names=["web.1.abc"],
    )

    assert ok is True
    assert called == ["web.1.abc"]
