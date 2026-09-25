from typing import Final

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.agent_client import AgentClientManager
from backend.core.jobs.jobs_coordinator import host_job_coordinator
from backend.db.session import get_async_session
from backend.modules.auth.auth_util import is_authorized_req
from backend.modules.hosts.hosts_model import HostsModel
from backend.modules.hosts.hosts_util import get_host
from backend.modules.services.services_schemas import (
    ServiceListItem,
    ServicePatchBody,
    ServiceTriggerRequestBody,
)
from backend.modules.services.services_util import (
    get_host_services,
    get_or_create_service,
    merge_service_items,
)

services_router = APIRouter(
    prefix="/hosts/{host_id}/services",
    tags=["services"],
    dependencies=[Depends(is_authorized_req)],
)


def _raise_for_host_status(host: HostsModel) -> None:
    if not host.enabled:
        raise HTTPException(status.HTTP_409_CONFLICT, "Host disabled")
    if not host.is_swarm:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Host is not a Swarm manager")


@services_router.get(
    "",
    response_model=list[ServiceListItem],
    description="Get list of Swarm services for a host",
)
async def list_services(
    host_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> list[ServiceListItem]:
    host = await get_host(host_id, session)
    _raise_for_host_status(host)

    client = AgentClientManager.get_host_client(host)
    agent_services = await client.service.list()
    db_services = await get_host_services(session, host_id)

    return merge_service_items(agent_services, db_services)


@services_router.patch(
    "/{service_name}",
    response_model=ServiceListItem,
    description="Update settings for a Swarm service",
)
async def patch_service(
    host_id: int,
    service_name: str,
    body: ServicePatchBody,
    session: AsyncSession = Depends(get_async_session),
) -> ServiceListItem:
    host = await get_host(host_id, session)
    _raise_for_host_status(host)
    client = AgentClientManager.get_host_client(host)

    # Fetch service details from agent to get service_id and image
    agent_services = await client.service.list()
    target_svc = next((s for s in agent_services if s.name == service_name), None)
    if target_svc is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Service {service_name} not found on host {host.name}",
        )

    db_item = await get_or_create_service(
        session,
        host_id,
        service_id=target_svc.id,
        name=service_name,
        image=target_svc.image,
    )

    if body.check_enabled is not None:
        db_item.check_enabled = body.check_enabled
    if body.update_enabled is not None:
        db_item.update_enabled = body.update_enabled

    await session.commit()
    await session.refresh(db_item)

    merged = merge_service_items([target_svc], [db_item])
    return merged[0]


@services_router.post(
    "/check",
    description="Trigger manual check for Swarm services on a host",
)
async def check_services(
    host_id: int,
    body: ServiceTriggerRequestBody | None = None,
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, str]:
    host = await get_host(host_id, session)
    _raise_for_host_status(host)
    names = body.names if body else None
    await host_job_coordinator.submit(
        host,
        "check_services",
        names=names,
        manual=True,
        wait=False,
    )
    return {"detail": "Check job submitted"}


@services_router.post(
    "/update",
    description="Trigger manual update for Swarm services on a host",
)
async def update_services(
    host_id: int,
    body: ServiceTriggerRequestBody | None = None,
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, str]:
    host = await get_host(host_id, session)
    _raise_for_host_status(host)
    names = body.names if body else None
    await host_job_coordinator.submit(
        host,
        "update_services",
        names=names,
        manual=True,
        wait=False,
    )
    return {"detail": "Update job submitted"}


@services_router.get(
    "/{service_name}/logs",
    description="Get aggregated logs for a Swarm service",
)
async def service_logs(
    host_id: int,
    service_name: str,
    tail: int = 100,
    timestamps: bool = False,
    session: AsyncSession = Depends(get_async_session),
) -> Response:
    host = await get_host(host_id, session)
    _raise_for_host_status(host)
    client: Final = AgentClientManager.get_host_client(host)
    logs = await client.service.logs(
        service_name,
        tail=tail,
        timestamps=timestamps,
    )
    return Response(content=logs, media_type="text/plain")
