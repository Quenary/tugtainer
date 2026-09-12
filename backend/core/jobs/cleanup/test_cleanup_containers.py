from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from backend.core.jobs.cleanup.cleanup_containers import (
    cleanup_all_stale_containers,
    cleanup_host_stale_containers,
)
from backend.modules.hosts.hosts_model import HostsModel

base_module = "backend.core.jobs.cleanup.cleanup_containers"


@pytest.mark.asyncio
async def test_cleanup_clears_update_available_for_missing_containers(
    mocker: MockerFixture,
):
    host = cast(
        HostsModel, cast(object, SimpleNamespace(id=1, name="local", enabled=True))
    )

    session = AsyncMock()
    session.commit = AsyncMock()

    active_db = SimpleNamespace(
        id=1,
        name="portainer_agent",
        host_id=1,
        update_available=True,
        check_enabled=True,
        update_enabled=False,
    )
    stale_db = SimpleNamespace(
        id=2,
        name="cardholder_pwa-app-1",
        host_id=1,
        update_available=True,
        check_enabled=True,
        update_enabled=True,
        delay_update_for=120,
    )

    db_result_mock = MagicMock()
    db_result_mock.scalars.return_value.all.return_value = [active_db, stale_db]
    session.execute.return_value = db_result_mock

    client_manager_mock = mocker.patch(f"{base_module}.AgentClientManager")
    host_client = MagicMock()
    agent_container = SimpleNamespace(name="portainer_agent")
    host_client.container.list = AsyncMock(return_value=[agent_container])
    client_manager_mock.get_host_client.return_value = host_client

    await cleanup_host_stale_containers(host, session)

    assert active_db.update_available is True
    assert stale_db.update_available is False
    assert stale_db.check_enabled is True
    assert stale_db.update_enabled is True
    assert stale_db.delay_update_for == 120
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_cleanup_skips_when_no_flags_to_clear(
    mocker: MockerFixture,
):
    host = cast(
        HostsModel, cast(object, SimpleNamespace(id=1, name="local", enabled=True))
    )

    session = AsyncMock()
    session.commit = AsyncMock()

    stale_db = SimpleNamespace(
        id=2,
        name="cardholder_pwa-app-1",
        host_id=1,
        update_available=False,
        check_enabled=True,
    )

    db_result_mock = MagicMock()
    db_result_mock.scalars.return_value.all.return_value = [stale_db]
    session.execute.return_value = db_result_mock

    client_manager_mock = mocker.patch(f"{base_module}.AgentClientManager")
    host_client = MagicMock()
    host_client.container.list = AsyncMock(return_value=[])
    client_manager_mock.get_host_client.return_value = host_client

    await cleanup_host_stale_containers(host, session)

    assert stale_db.update_available is False
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_cleanup_skips_host_on_agent_error(
    mocker: MockerFixture,
):
    host = cast(
        HostsModel, cast(object, SimpleNamespace(id=1, name="local", enabled=True))
    )

    session = AsyncMock()
    session.commit = AsyncMock()

    client_manager_mock = mocker.patch(f"{base_module}.AgentClientManager")
    host_client = MagicMock()
    host_client.container.list = AsyncMock(
        side_effect=RuntimeError("Connection refused")
    )
    client_manager_mock.get_host_client.return_value = host_client

    await cleanup_host_stale_containers(host, session)

    session.execute.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_cleanup_skips_disabled_host(
    mocker: MockerFixture,
):
    host = cast(
        HostsModel,
        cast(object, SimpleNamespace(id=1, name="disabled_host", enabled=False)),
    )

    session = AsyncMock()
    client_manager_mock = mocker.patch(f"{base_module}.AgentClientManager")

    await cleanup_host_stale_containers(host, session)

    client_manager_mock.get_host_client.assert_not_called()
    session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_cleanup_all_stale_containers(
    mocker: MockerFixture,
):
    host1 = cast(
        HostsModel, cast(object, SimpleNamespace(id=1, name="host1", enabled=True))
    )
    host2 = cast(
        HostsModel, cast(object, SimpleNamespace(id=2, name="host2", enabled=True))
    )

    session = AsyncMock()
    db_result_mock = MagicMock()
    db_result_mock.scalars.return_value.all.return_value = [host1, host2]
    session.execute.return_value = db_result_mock

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    mocker.patch(f"{base_module}.async_session_maker", return_value=session_cm)

    cleanup_host_mock = mocker.patch(
        f"{base_module}.cleanup_host_stale_containers", new_callable=AsyncMock
    )

    await cleanup_all_stale_containers()

    assert cleanup_host_mock.await_count == 2
    cleanup_host_mock.assert_any_await(host1, session)
    cleanup_host_mock.assert_any_await(host2, session)
