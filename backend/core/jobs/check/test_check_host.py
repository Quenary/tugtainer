from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture
from python_on_whales.components.container.models import (
    ContainerConfig,
    ContainerInspectResult,
)

from backend.const import TUGTAINER_HIDDEN_LABEL
from backend.core.jobs.check.check_host import run_check_host_job
from backend.testing import patch_async_session

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
