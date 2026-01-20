from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core import HostsManager
from backend.core.auth.auth_provider_chore import is_authorized
from backend.exception import TugAgentClientError
from backend.schemas import (
    HostInfo,
    HostBase,
    HostStatusResponseBody,
    HostSummary,
)
from backend.db.session import get_async_session
from backend.db.models import HostsModel, ContainersModel
from backend.api.util import get_host, map_container_schema
from shared.schemas.container_schemas import GetContainerListBodySchema

router = APIRouter(
    prefix="/hosts",
    tags=["hosts"],
    dependencies=[Depends(is_authorized)],
)


@router.get(
    "/list",
    response_model=list[HostInfo],
    description="Get list of existing hosts",
)
async def get_list(
    session: AsyncSession = Depends(get_async_session),
):
    stmt = select(HostsModel)
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get(
    path="/summary",
    description="Get summary statistics for all hosts",
    response_model=list[HostSummary],
)
async def get_summary(
    session: AsyncSession = Depends(get_async_session),
) -> list[HostSummary]:
    stmt = select(HostsModel)
    result = await session.execute(stmt)
    hosts = result.scalars().all()

    summaries = []
    for host in hosts:
        if not host.enabled:
            summaries.append(HostSummary(
                host_id=host.id,
                host_name=host.name,
                total_containers=0,
                by_status={},
                by_health={},
                by_protected={"true": 0, "false": 0},
                by_check_enabled={"true": 0, "false": 0},
                by_update_enabled={"true": 0, "false": 0},
                by_update_available={"true": 0, "false": 0},
            ))
            continue

        client = HostsManager.get_host_client(host)
        containers = await client.container.list(
            GetContainerListBodySchema(all=True)
        )

        db_result = await session.execute(
            select(ContainersModel).where(
                ContainersModel.host_id == host.id
            )
        )
        containers_db = db_result.scalars().all()

        mapped_containers = []
        for c in containers:
            db_item = next(
                (item for item in containers_db if item.name == c.name),
                None,
            )
            mapped_containers.append(
                map_container_schema(host.id, c, db_item)
            )

        by_status = {}
        by_health = {}
        by_protected = {"true": 0, "false": 0}
        by_check_enabled = {"true": 0, "false": 0}
        by_update_enabled = {"true": 0, "false": 0}
        by_update_available = {"true": 0, "false": 0}

        for container in mapped_containers:
            if container.status:
                by_status[container.status] = by_status.get(container.status, 0) + 1

            health_key = container.health or "none"
            by_health[health_key] = by_health.get(health_key, 0) + 1

            protected_key = "true" if container.protected else "false"
            by_protected[protected_key] += 1

            if container.check_enabled is not None:
                check_key = "true" if container.check_enabled else "false"
                by_check_enabled[check_key] += 1

            if container.update_enabled is not None:
                update_key = "true" if container.update_enabled else "false"
                by_update_enabled[update_key] += 1

            if container.update_available is not None:
                avail_key = "true" if container.update_available else "false"
                by_update_available[avail_key] += 1

        summaries.append(HostSummary(
            host_id=host.id,
            host_name=host.name,
            total_containers=len(mapped_containers),
            by_status=by_status,
            by_health=by_health,
            by_protected=by_protected,
            by_check_enabled=by_check_enabled,
            by_update_enabled=by_update_enabled,
            by_update_available=by_update_available,
        ))

    return summaries


@router.post(
    path="",
    response_model=HostInfo,
    status_code=201,
    description="Create host",
)
async def create(
    body: HostBase,
    session: AsyncSession = Depends(get_async_session),
):
    stmt = (
        select(HostsModel)
        .where(HostsModel.name == body.name)
        .limit(1)
    )
    result = await session.execute(stmt)
    host = result.scalar_one_or_none()
    if host:
        raise HTTPException(400, "Host name is already taken")
    _body = body.model_dump(exclude_unset=True)
    new_host = HostsModel(**_body)
    session.add(new_host)
    await session.commit()
    await session.refresh(new_host)
    if new_host.enabled:
        HostsManager.set_client(new_host)
    return new_host


@router.get(
    path="/{id}",
    response_model=HostInfo,
    description="Get host info",
)
async def read(
    id: int,
    session: AsyncSession = Depends(get_async_session),
):
    return await get_host(id, session)


@router.put(
    path="/{id}",
    response_model=HostInfo,
    description="Update host info",
)
async def update(
    id: int,
    body: HostBase,
    session: AsyncSession = Depends(get_async_session),
):
    host = await get_host(id, session)
    for key, value in body.model_dump(exclude_unset=True).items():
        if getattr(host, key) != value:
            setattr(host, key, value)
    await session.commit()
    await session.refresh(host)
    HostsManager.remove_client(host.id)
    if host.enabled:
        HostsManager.set_client(host)
    return host


@router.delete(path="/{id}", description="Delete host")
async def delete(
    id: int,
    session: AsyncSession = Depends(get_async_session),
):
    host = await get_host(id, session)
    HostsManager.remove_client(host)
    await session.delete(host)
    await session.commit()
    return {"detail": "Host deleted successfully"}


@router.get(
    path="/{id}/status",
    description="Get host status",
    response_model=HostStatusResponseBody,
)
async def get_status(
    id: int,
    response: Response,
    session: AsyncSession = Depends(get_async_session),
) -> HostStatusResponseBody:
    response.headers["Cache-Control"] = (
        "no-cache, no-store, must-revalidate"
    )
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    host = await get_host(id, session)
    if not host.enabled:
        return HostStatusResponseBody(id=id)
    client = HostsManager.get_host_client(host)
    try:
        _ = await client.public.health()
        _ = await client.public.access()
        return HostStatusResponseBody(id=id, ok=True)
    except TugAgentClientError as e:
        return HostStatusResponseBody(
            id=id,
            ok=False,
            err=str(e),
        )
    except Exception as e:
        return HostStatusResponseBody(
            id=id,
            ok=False,
            err=f"Unknown error\n{str(e)}",
        )
