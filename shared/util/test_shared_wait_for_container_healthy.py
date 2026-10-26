from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture
from python_on_whales.components.container.models import ContainerInspectResult

from shared.util.wait_for_container_healthy import wait_for_container_healthy

base_module = "shared.util.wait_for_container_healthy"


def _container(
    status: str | None = "running",
    health: str | None = None,
    id: str | None = "c1",
) -> ContainerInspectResult:
    state = SimpleNamespace(
        status=status,
        health=SimpleNamespace(status=health) if health else None,
    )
    return cast(ContainerInspectResult, SimpleNamespace(id=id, state=state))


@pytest.mark.asyncio
async def test_wait_returns_false_without_container_id() -> None:
    inspect = AsyncMock()
    container = _container(id=None)

    ok, got = await wait_for_container_healthy(inspect, container, timeout=1)

    assert ok is False
    assert got is container
    inspect.assert_not_called()


@pytest.mark.asyncio
async def test_wait_returns_when_healthcheck_becomes_healthy(
    mocker: MockerFixture,
) -> None:
    mocker.patch(f"{base_module}.time.time", side_effect=[0, 0, 0])
    sleep = mocker.patch(f"{base_module}.asyncio.sleep", new=AsyncMock())
    starting = _container(health="starting")
    healthy = _container(health="healthy")
    inspect = AsyncMock(side_effect=[starting, healthy])

    ok, got = await wait_for_container_healthy(inspect, starting, timeout=30)

    assert ok is True
    assert got is healthy
    sleep.assert_awaited_once_with(5)


@pytest.mark.asyncio
async def test_wait_without_healthcheck_returns_when_running(
    mocker: MockerFixture,
) -> None:
    mocker.patch(f"{base_module}.time.time", side_effect=[0, 0])
    running = _container()
    inspect = AsyncMock(return_value=running)

    ok, got = await wait_for_container_healthy(inspect, running, timeout=30)

    assert ok is True
    assert got is running


@pytest.mark.parametrize(
    ("status", "health", "expected"),
    [
        ("running", "unknown", True),
        ("running", "healthy", True),
        ("running", "unhealthy", False),
        ("exited", "unknown", False),
    ],
)
@pytest.mark.asyncio
async def test_wait_final_attempt_after_timeout(
    mocker: MockerFixture,
    status: str,
    health: str,
    expected: bool,
) -> None:
    mocker.patch(f"{base_module}.time.time", side_effect=[0, 100])
    last = _container(status=status, health=health)
    inspect = AsyncMock(return_value=last)

    ok, got = await wait_for_container_healthy(
        inspect, _container(health="starting"), timeout=30
    )

    assert ok is expected
    assert got is last
    inspect.assert_awaited_once_with("c1")
