from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from backend.core.jobs.update.update_services import run_update_services_job
from backend.exception import TugAgentClientError
from backend.testing import make_service, patch_async_session
from backend.util.now import now

base_module = "backend.core.jobs.update.update_services"


@pytest.mark.asyncio
async def test_run_update_services_job_filters_by_names(mocker: MockerFixture):
    host = SimpleNamespace(id=1, name="test-host")
    client = MagicMock()

    s1 = make_service("svc-a")
    s2 = make_service("svc-b")
    s3 = make_service("svc-c")
    client.service.list = AsyncMock(return_value=[s1, s2, s3])

    session = MagicMock()
    patch_async_session(mocker, base_module, session)
    mocker.patch(f"{base_module}.get_host_services", AsyncMock(return_value=[]))

    updated: list[str] = []

    async def update_one(_client, _host, service, tracker=None):
        updated.append(service.name)
        return SimpleNamespace(service=service)

    mocker.patch(f"{base_module}.run_update_service_job", side_effect=update_one)
    tracker = MagicMock()

    ok = await run_update_services_job(
        host,  # type: ignore[arg-type]
        client,
        manual=True,
        names=["svc-b"],
        tracker=tracker,
    )

    assert ok is True
    assert updated == ["svc-b"]
    tracker.set_status.assert_called()


@pytest.mark.asyncio
async def test_run_update_services_job_auto_mode_filters_eligible(
    mocker: MockerFixture,
):
    host = SimpleNamespace(id=1, name="test-host")
    client = MagicMock()

    s1 = make_service("svc-enabled-available")
    s2 = make_service("svc-disabled")
    s3 = make_service("svc-no-update")
    client.service.list = AsyncMock(return_value=[s1, s2, s3])

    db1 = SimpleNamespace(
        name="svc-enabled-available",
        update_enabled=True,
        update_available=True,
        remote_digests_changed_at=None,
    )
    db2 = SimpleNamespace(
        name="svc-disabled",
        update_enabled=False,
        update_available=True,
        remote_digests_changed_at=None,
    )
    db3 = SimpleNamespace(
        name="svc-no-update",
        update_enabled=True,
        update_available=False,
        remote_digests_changed_at=None,
    )
    mocker.patch(f"{base_module}.SettingsStorage.get", return_value=0)

    session = MagicMock()
    patch_async_session(mocker, base_module, session)
    mocker.patch(
        f"{base_module}.get_host_services", AsyncMock(return_value=[db1, db2, db3])
    )

    updated: list[str] = []

    async def update_one(_client, _host, service, tracker=None):
        updated.append(service.name)
        return SimpleNamespace(service=service)

    mocker.patch(f"{base_module}.run_update_service_job", side_effect=update_one)
    tracker = MagicMock()

    ok = await run_update_services_job(
        host,  # type: ignore[arg-type]
        client,
        manual=False,
        names=None,
        tracker=tracker,
    )

    assert ok is True
    assert updated == ["svc-enabled-available"]


@pytest.mark.asyncio
async def test_run_update_services_job_manual_all(mocker: MockerFixture):
    host = SimpleNamespace(id=1, name="test-host")
    client = MagicMock()

    s1 = make_service("svc-1")
    s2 = make_service("svc-2")
    client.service.list = AsyncMock(return_value=[s1, s2])

    session = MagicMock()
    patch_async_session(mocker, base_module, session)
    mocker.patch(f"{base_module}.get_host_services", AsyncMock(return_value=[]))

    updated: list[str] = []

    async def update_one(_client, _host, service, tracker=None):
        updated.append(service.name)
        return SimpleNamespace(service=service)

    mocker.patch(f"{base_module}.run_update_service_job", side_effect=update_one)
    tracker = MagicMock()

    ok = await run_update_services_job(
        host,  # type: ignore[arg-type]
        client,
        manual=True,
        names=None,
        tracker=tracker,
    )

    assert ok is True
    assert updated == ["svc-1", "svc-2"]


@pytest.mark.asyncio
async def test_run_update_services_job_require_available_skips_current(
    mocker: MockerFixture,
):
    host = SimpleNamespace(id=1, name="test-host")
    client = MagicMock()
    ready = make_service("ready")
    current = make_service("current")
    client.service.list = AsyncMock(return_value=[ready, current])
    patch_async_session(mocker, base_module, MagicMock())
    mocker.patch(
        f"{base_module}.get_host_services",
        AsyncMock(
            return_value=[
                SimpleNamespace(name="ready", update_available=True),
                SimpleNamespace(name="current", update_available=False),
            ]
        ),
    )
    updated: list[str] = []

    async def update_one(_client, _host, service, tracker=None):
        updated.append(service.name)

    mocker.patch(f"{base_module}.run_update_service_job", side_effect=update_one)

    ok = await run_update_services_job(
        host,  # type: ignore[arg-type]
        client,
        manual=True,
        require_available=True,
        tracker=MagicMock(),
    )

    assert ok is True
    assert updated == ["ready"]


@pytest.mark.asyncio
async def test_run_update_services_job_respects_delay(mocker: MockerFixture):
    host = SimpleNamespace(id=1, name="test-host")
    client = MagicMock()
    recent = make_service("recent")
    old = make_service("old")
    client.service.list = AsyncMock(return_value=[recent, old])
    patch_async_session(mocker, base_module, MagicMock())
    mocker.patch(f"{base_module}.SettingsStorage.get", return_value=3600)
    mocker.patch(
        f"{base_module}.get_host_services",
        AsyncMock(
            return_value=[
                SimpleNamespace(
                    name="recent",
                    update_enabled=True,
                    update_available=True,
                    remote_digests_changed_at=now() - timedelta(seconds=10),
                ),
                SimpleNamespace(
                    name="old",
                    update_enabled=True,
                    update_available=True,
                    remote_digests_changed_at=now() - timedelta(seconds=7200),
                ),
            ]
        ),
    )
    updated: list[str] = []

    async def update_one(_client, _host, service, tracker=None):
        updated.append(service.name)

    mocker.patch(f"{base_module}.run_update_service_job", side_effect=update_one)

    ok = await run_update_services_job(
        host,  # type: ignore[arg-type]
        client,
        manual=False,
        tracker=MagicMock(),
    )

    assert ok is True
    assert updated == ["old"]


@pytest.mark.asyncio
async def test_run_update_services_job_stale_swarm_is_not_a_failure(
    mocker: MockerFixture,
):
    host = SimpleNamespace(id=1, name="test-host")
    client = MagicMock()
    client.service.list = AsyncMock(
        side_effect=TugAgentClientError(
            "Agent request error", "http://agent", "GET", 503, "not a manager"
        )
    )
    patch_async_session(mocker, base_module, MagicMock())

    ok = await run_update_services_job(
        host,  # type: ignore[arg-type]
        client,
        tracker=MagicMock(),
    )

    assert ok is True
