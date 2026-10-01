from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture
from python_on_whales.components.container.models import ContainerInspectResult

from backend.core.container_util.wait_for_container_healthy import (
    wait_for_container_healthy,
)

base_module = "backend.core.container_util.wait_for_container_healthy"


@pytest.mark.asyncio
async def test_wait_returns_false_without_container_id() -> None:
    client = AsyncMock()
    container = SimpleNamespace(id=None, state=None)

    ok, got = await wait_for_container_healthy(
        client, cast(ContainerInspectResult, container), timeout=1
    )

    assert ok is False
    assert got is container
    client.container.inspect.assert_not_called()


@pytest.mark.asyncio
async def test_wait_returns_when_healthcheck_becomes_healthy(
    mocker: MockerFixture,
) -> None:
    mocker.patch(f"{base_module}.time.time", side_effect=[0, 0])
    mocker.patch(f"{base_module}.asyncio.sleep", new=AsyncMock())
    mocker.patch(
        f"{base_module}.get_container_health_status_str", return_value="healthy"
    )
    inspected = SimpleNamespace(id="c1")
    client = AsyncMock()
    client.container.inspect = AsyncMock(return_value=inspected)
    container = SimpleNamespace(id="c1", state=SimpleNamespace(health=object()))

    ok, got = await wait_for_container_healthy(
        client, cast(ContainerInspectResult, container), timeout=30
    )

    assert ok is True
    assert got is inspected


@pytest.mark.asyncio
async def test_wait_accepts_unknown_health_on_timeout(
    mocker: MockerFixture,
) -> None:
    mocker.patch(f"{base_module}.time.time", side_effect=[0, 100])
    mocker.patch(
        f"{base_module}.get_container_health_status_str", return_value="unknown"
    )
    mocker.patch(f"{base_module}.is_running_container", return_value=True)
    inspected = SimpleNamespace(id="c1")
    client = AsyncMock()
    client.container.inspect = AsyncMock(return_value=inspected)
    container = SimpleNamespace(id="c1", state=SimpleNamespace(health=object()))

    ok, got = await wait_for_container_healthy(
        client, cast(ContainerInspectResult, container), timeout=30
    )

    assert ok is True
    assert got is inspected
    client.container.inspect.assert_awaited_once_with("c1")
