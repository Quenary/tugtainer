from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from backend.core.jobs.check.check_services import run_check_services_job
from shared.schemas.service_schemas import ServiceListItemSchema, ServiceReplicasSchema

base_module = "backend.core.jobs.check.check_services"


def _make_service(name: str) -> ServiceListItemSchema:
    return ServiceListItemSchema(
        id=f"id-{name}",
        name=name,
        image=f"repo/{name}:latest",
        mode="replicated",
        replicas=ServiceReplicasSchema(running=1, desired=1),
    )


@pytest.mark.asyncio
async def test_run_check_services_job_filters_by_names(mocker: MockerFixture):
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

    called: list[str] = []

    async def check_one(_client, _host, service, tracker=None):
        called.append(service.name)
        return SimpleNamespace(service=service)

    mocker.patch(f"{base_module}.run_check_service_job", side_effect=check_one)
    tracker = MagicMock()

    ok = await run_check_services_job(
        host,  # type: ignore[arg-type]
        client,
        names=["svc-c", "svc-a"],
        tracker=tracker,
    )

    assert ok is True
    assert called == ["svc-a", "svc-c"]
    tracker.set_status.assert_called()


@pytest.mark.asyncio
async def test_run_check_services_job_empty_list(mocker: MockerFixture):
    host = SimpleNamespace(id=1, name="test-host")
    client = MagicMock()
    client.service.list = AsyncMock(return_value=[])

    session = MagicMock()
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    mocker.patch(f"{base_module}.async_session_maker", return_value=session_cm)
    mocker.patch(f"{base_module}.get_host_services", AsyncMock(return_value=[]))

    tracker = MagicMock()
    ok = await run_check_services_job(
        host,  # type: ignore[arg-type]
        client,
        tracker=tracker,
    )

    assert ok is True
    tracker.set_status.assert_called()
