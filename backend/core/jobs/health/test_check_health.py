from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from backend.core.jobs.health.check_health import (
    HealthMonitorNotificationBatchItem,
    _do_check_host_health,
    _send_health_notifications,
    check_all_containers_health,
)
from backend.modules.health.health_model import ContainerHealthState
from backend.modules.settings.settings_enum import ESettingKey

base_module = "backend.core.jobs.health.check_health"


@pytest.mark.asyncio
async def test_do_check_host_health_inserts_missing_container(mocker: MockerFixture):
    host = SimpleNamespace(id=1, name="host1", enabled=True, container_hc_timeout=60)

    session = AsyncMock()
    session.get.return_value = host
    session.add = MagicMock()

    db_containers_mock = MagicMock()
    db_containers_mock.scalars.return_value.all.return_value = []
    session.execute.return_value = db_containers_mock

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    mocker.patch(f"{base_module}.async_session_maker", return_value=session_cm)

    client_manager_mock = mocker.patch(f"{base_module}.AgentClientManager")
    host_client = MagicMock()

    agent_container = SimpleNamespace(
        id="c1",
        name="test_container",
        state=SimpleNamespace(health=SimpleNamespace()),
    )
    host_client.container.list = AsyncMock(return_value=[agent_container])
    client_manager_mock.get_host_client.return_value = host_client

    mocker.patch(f"{base_module}.SettingsStorage.get", return_value="1")
    mocker.patch(
        f"{base_module}.get_container_health_status_str", return_value="healthy"
    )

    insert_mock = AsyncMock(
        return_value=SimpleNamespace(id=1, healthcheck_timeout=None)
    )
    mocker.patch(f"{base_module}.insert_or_update_container", insert_mock)

    state_mock_result = MagicMock()
    state_mock_result.scalar_one_or_none.return_value = None
    session.execute.side_effect = [db_containers_mock, state_mock_result]

    await _do_check_host_health(1)

    insert_mock.assert_called_once_with(
        session=session,
        host_id=1,
        c_name="test_container",
        c_data={},
    )

    assert session.add.call_count >= 2  # State and History
    session.commit.assert_called()


@pytest.mark.asyncio
async def test_do_check_host_health_skips_container_without_healthcheck(
    mocker: MockerFixture,
):
    host = SimpleNamespace(id=1, name="host1", enabled=True, container_hc_timeout=60)

    session = AsyncMock()
    session.get.return_value = host
    session.add = MagicMock()

    db_containers_mock = MagicMock()
    db_containers_mock.scalars.return_value.all.return_value = []
    session.execute.return_value = db_containers_mock

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    mocker.patch(f"{base_module}.async_session_maker", return_value=session_cm)

    client_manager_mock = mocker.patch(f"{base_module}.AgentClientManager")
    host_client = MagicMock()

    agent_container = SimpleNamespace(
        id="c1",
        name="no_hc_container",
        state=SimpleNamespace(health=None),
    )
    host_client.container.list = AsyncMock(return_value=[agent_container])
    client_manager_mock.get_host_client.return_value = host_client

    insert_mock = AsyncMock()
    mocker.patch(f"{base_module}.insert_or_update_container", insert_mock)

    await _do_check_host_health(1)

    # Should not insert or process health for container without healthcheck
    insert_mock.assert_not_called()
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_do_check_host_health_unhealthy_triggers_restart_and_notification(
    mocker: MockerFixture,
):
    host = SimpleNamespace(id=1, name="host1", enabled=True, container_hc_timeout=60)

    session = AsyncMock()
    session.get.return_value = host
    session.add = MagicMock()

    db_container = SimpleNamespace(id=1, name="unhealthy_app", healthcheck_timeout=30)
    db_containers_mock = MagicMock()
    db_containers_mock.scalars.return_value.all.return_value = [db_container]

    existing_state = ContainerHealthState(
        host_id=1,
        container_id=1,
        consecutive_failures=1,
        restart_attempts=0,
        is_notified=False,
    )
    state_mock_result = MagicMock()
    state_mock_result.scalar_one_or_none.return_value = existing_state

    session.execute.side_effect = [db_containers_mock, state_mock_result]

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    mocker.patch(f"{base_module}.async_session_maker", return_value=session_cm)

    client_manager_mock = mocker.patch(f"{base_module}.AgentClientManager")
    host_client = MagicMock()
    agent_container = SimpleNamespace(
        id="c1",
        name="unhealthy_app",
        state=SimpleNamespace(health=SimpleNamespace()),
    )
    host_client.container.list = AsyncMock(return_value=[agent_container])
    host_client.container.restart = AsyncMock()
    client_manager_mock.get_host_client.return_value = host_client

    # n_to_restart=2, n_to_ntfy=2, max_restarts=3
    def mock_settings(key: ESettingKey):
        if key == ESettingKey.HEALTH_MONITOR_N_TO_RESTART:
            return "2"
        if key == ESettingKey.HEALTH_MONITOR_N_TO_NTFY:
            return "2"
        if key == ESettingKey.HEALTH_MONITOR_RESTART_ATTEMPTS:
            return "3"
        return None

    mocker.patch(f"{base_module}.SettingsStorage.get", side_effect=mock_settings)
    mocker.patch(
        f"{base_module}.get_container_health_status_str", return_value="unhealthy"
    )
    mocker.patch(f"{base_module}.wait_for_container_healthy", AsyncMock())
    send_notif_mock = mocker.patch(
        f"{base_module}._send_health_notifications", AsyncMock()
    )

    await _do_check_host_health(1)

    assert existing_state.consecutive_failures == 2
    assert existing_state.restart_attempts == 1
    assert existing_state.is_notified is True
    host_client.container.restart.assert_awaited_once_with("c1")
    send_notif_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_do_check_host_health_healthy_resets_state(mocker: MockerFixture):
    host = SimpleNamespace(id=1, name="host1", enabled=True, container_hc_timeout=60)

    session = AsyncMock()
    session.get.return_value = host
    session.add = MagicMock()

    db_container = SimpleNamespace(id=1, name="recovering_app", healthcheck_timeout=30)
    db_containers_mock = MagicMock()
    db_containers_mock.scalars.return_value.all.return_value = [db_container]

    existing_state = ContainerHealthState(
        host_id=1,
        container_id=1,
        consecutive_failures=5,
        restart_attempts=2,
        is_notified=True,
    )
    state_mock_result = MagicMock()
    state_mock_result.scalar_one_or_none.return_value = existing_state

    session.execute.side_effect = [db_containers_mock, state_mock_result]

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    mocker.patch(f"{base_module}.async_session_maker", return_value=session_cm)

    client_manager_mock = mocker.patch(f"{base_module}.AgentClientManager")
    host_client = MagicMock()
    agent_container = SimpleNamespace(
        id="c1",
        name="recovering_app",
        state=SimpleNamespace(health=SimpleNamespace()),
    )
    host_client.container.list = AsyncMock(return_value=[agent_container])
    client_manager_mock.get_host_client.return_value = host_client

    mocker.patch(f"{base_module}.SettingsStorage.get", return_value="2")
    mocker.patch(
        f"{base_module}.get_container_health_status_str", return_value="healthy"
    )
    send_notif_mock = mocker.patch(
        f"{base_module}._send_health_notifications", AsyncMock()
    )

    await _do_check_host_health(1)

    assert existing_state.consecutive_failures == 0
    assert existing_state.restart_attempts == 0
    assert existing_state.is_notified is False
    send_notif_mock.assert_awaited_once_with(
        "host1",
        [
            {
                "container": agent_container,
                "status": "healthy",
            }
        ],
    )


@pytest.mark.asyncio
async def test_do_check_host_health_healthy_does_not_notify_if_not_previously_notified(
    mocker: MockerFixture,
):
    host = SimpleNamespace(id=1, name="host1", enabled=True, container_hc_timeout=60)

    session = AsyncMock()
    session.get.return_value = host
    session.add = MagicMock()

    db_container = SimpleNamespace(id=1, name="normal_app", healthcheck_timeout=30)
    db_containers_mock = MagicMock()
    db_containers_mock.scalars.return_value.all.return_value = [db_container]

    existing_state = ContainerHealthState(
        host_id=1,
        container_id=1,
        consecutive_failures=0,
        restart_attempts=0,
        is_notified=False,
    )
    state_mock_result = MagicMock()
    state_mock_result.scalar_one_or_none.return_value = existing_state

    session.execute.side_effect = [db_containers_mock, state_mock_result]

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    mocker.patch(f"{base_module}.async_session_maker", return_value=session_cm)

    client_manager_mock = mocker.patch(f"{base_module}.AgentClientManager")
    host_client = MagicMock()
    agent_container = SimpleNamespace(
        id="c1",
        name="normal_app",
        state=SimpleNamespace(health=SimpleNamespace()),
    )
    host_client.container.list = AsyncMock(return_value=[agent_container])
    client_manager_mock.get_host_client.return_value = host_client

    mocker.patch(f"{base_module}.SettingsStorage.get", return_value="2")
    mocker.patch(
        f"{base_module}.get_container_health_status_str", return_value="healthy"
    )
    send_notif_mock = mocker.patch(
        f"{base_module}._send_health_notifications", AsyncMock()
    )

    await _do_check_host_health(1)

    assert existing_state.consecutive_failures == 0
    assert existing_state.restart_attempts == 0
    assert existing_state.is_notified is False
    send_notif_mock.assert_not_called()


@pytest.mark.asyncio
async def test_send_health_notifications(mocker: MockerFixture):
    template = "{% for host, items in groups.items() %}{{ host }}: {% for it in items %}{{ it.container.name }}={{ it.status }}{% endfor %}{% endfor %}"

    def mock_settings(key: ESettingKey):
        if key == ESettingKey.HEALTH_MONITOR_NTFY_BODY_TMPL:
            return template
        if key == ESettingKey.NOTIFICATION_URLS:
            return "https://ntfy.sh/my_topic\nhttps://discord.com/webhook"
        return None

    mocker.patch(f"{base_module}.SettingsStorage.get", side_effect=mock_settings)
    send_notif = mocker.patch(f"{base_module}.send_notification", AsyncMock())

    batch: list[HealthMonitorNotificationBatchItem] = [
        cast(
            HealthMonitorNotificationBatchItem,
            cast(
                object,
                {
                    "container": SimpleNamespace(name="nginx"),
                    "status": "unhealthy",
                },
            ),
        )
    ]

    await _send_health_notifications("main-server", batch)

    send_notif.assert_awaited_once_with(
        "Health Monitor Alert",
        "main-server: nginx=unhealthy",
        urls=["https://ntfy.sh/my_topic", "https://discord.com/webhook"],
    )


@pytest.mark.asyncio
async def test_check_all_containers_health(mocker: MockerFixture):
    host1 = SimpleNamespace(id=1, enabled=True)
    host2 = SimpleNamespace(id=2, enabled=True)

    session = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [host1, host2]
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    session.execute.return_value = result_mock

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    mocker.patch(f"{base_module}.async_session_maker", return_value=session_cm)

    check_host_mock = mocker.patch(f"{base_module}._check_host_health", AsyncMock())

    await check_all_containers_health()

    assert check_host_mock.call_count == 2
    check_host_mock.assert_any_call(1)
    check_host_mock.assert_any_call(2)
