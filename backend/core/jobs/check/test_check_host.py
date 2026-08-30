from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from backend.core.jobs.check.check_host import run_check_host_job

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
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    mocker.patch(f"{base_module}.async_session_maker", return_value=session_cm)
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
