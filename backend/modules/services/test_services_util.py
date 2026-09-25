from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

import backend.modules.containers.containers_model  # noqa: F401
import backend.modules.health.health_model  # noqa: F401
import backend.modules.hosts.hosts_model  # noqa: F401
from backend.modules.services.services_model import SwarmServicesModel
from backend.modules.services.services_util import (
    get_host_services,
    get_or_create_service,
    merge_service_items,
)
from shared.schemas.service_schemas import ServiceListItemSchema, ServiceReplicasSchema


@pytest.mark.asyncio
async def test_get_host_services():
    session = MagicMock()
    mock_item = SwarmServicesModel(
        id=1,
        host_id=10,
        service_id="svc-1",
        name="web",
        image="nginx:alpine",
    )
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_item]
    session.execute = AsyncMock(return_value=mock_result)

    result = await get_host_services(session, 10)

    assert len(result) == 1
    assert result[0].name == "web"
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_or_create_service_existing():
    session = MagicMock()
    existing = SwarmServicesModel(
        id=1,
        host_id=10,
        service_id="svc-1",
        name="web",
        image="nginx:alpine",
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing
    session.execute = AsyncMock(return_value=mock_result)

    item = await get_or_create_service(
        session,
        host_id=10,
        service_id="svc-1",
        name="web",
        image="nginx:alpine",
    )

    assert item is existing
    assert not session.add.called


@pytest.mark.asyncio
async def test_get_or_create_service_new():
    session = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=mock_result)

    item = await get_or_create_service(
        session,
        host_id=10,
        service_id="svc-new",
        name="new-service",
        image="redis:latest",
    )

    assert item.name == "new-service"
    assert item.service_id == "svc-new"
    assert session.add.called
    assert session.commit.called
    assert session.refresh.called


def test_merge_service_items_with_db_match():
    now_dt = datetime.now()
    agent_svc = ServiceListItemSchema(
        id="svc-1",
        name="web",
        image="nginx:alpine",
        mode="replicated",
        replicas=ServiceReplicasSchema(running=2, desired=2),
        labels={"env": "prod"},
        update_status_state="completed",
        update_status_message="Update completed",
    )

    db_svc = SwarmServicesModel(
        id=1,
        host_id=10,
        service_id="svc-1",
        name="web",
        image="nginx:alpine",
        check_enabled=True,
        update_enabled=True,
        update_available=True,
        checked_at=now_dt,
        updated_at=now_dt,
    )

    merged = merge_service_items([agent_svc], [db_svc])

    assert len(merged) == 1
    m = merged[0]
    assert m.id == "svc-1"
    assert m.name == "web"
    assert m.image == "nginx:alpine"
    assert m.mode == "replicated"
    assert m.replicas_running == 2
    assert m.replicas_desired == 2
    assert m.check_enabled is True
    assert m.update_enabled is True
    assert m.update_available is True
    assert m.checked_at == now_dt
    assert m.updated_at == now_dt
    assert m.update_status_state == "completed"
    assert m.labels == {"env": "prod"}


def test_merge_service_items_without_db_match():
    agent_svc = ServiceListItemSchema(
        id="svc-2",
        name="worker",
        image="worker:latest",
        mode="global",
        replicas=ServiceReplicasSchema(running=5, desired=None),
    )

    merged = merge_service_items([agent_svc], [])

    assert len(merged) == 1
    m = merged[0]
    assert m.name == "worker"
    assert m.check_enabled is False
    assert m.update_enabled is False
    assert m.update_available is False
    assert m.checked_at is None
    assert m.updated_at is None
