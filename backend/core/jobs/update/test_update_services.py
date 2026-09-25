from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from backend.core.jobs.update.update_services import run_update_services_job
from shared.schemas.service_schemas import ServiceListItemSchema, ServiceReplicasSchema

base_module = "backend.core.jobs.update.update_services"


def _make_service(name: str) -> ServiceListItemSchema:
    return ServiceListItemSchema(
        id=f"id-{name}",
        name=name,
        image=f"repo/{name}:latest",
        mode="replicated",
        replicas=ServiceReplicasSchema(running=1, desired=1),
    )


@pytest.mark.asyncio
async def test_run_update_services_job_filters_by_names(mocker: MockerFixture):
    host = SimpleNamespace(id=1, name="test-host")
    client = MagicMock()

    s1 = _make_service("svc-a")
    s2 = _make_service("svc-b")
    s3 = _make_service("svc-c")
    client.service.list = AsyncMock(return_value=[s1, s2, s3])

    session = MagicMock()
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    mocker.patch(f"{base_module}.async_session_maker", return_value=session_cm)
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

    s1 = _make_service("svc-enabled-available")
    s2 = _make_service("svc-disabled")
    s3 = _make_service("svc-no-update")
    client.service.list = AsyncMock(return_value=[s1, s2, s3])

    db1 = SimpleNamespace(
        name="svc-enabled-available", update_enabled=True, update_available=True
    )
    db2 = SimpleNamespace(
        name="svc-disabled", update_enabled=False, update_available=True
    )
    db3 = SimpleNamespace(
        name="svc-no-update", update_enabled=True, update_available=False
    )

    session = MagicMock()
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    mocker.patch(f"{base_module}.async_session_maker", return_value=session_cm)
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

    s1 = _make_service("svc-1")
    s2 = _make_service("svc-2")
    client.service.list = AsyncMock(return_value=[s1, s2])

    session = MagicMock()
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    mocker.patch(f"{base_module}.async_session_maker", return_value=session_cm)
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
