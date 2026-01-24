import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.auth.auth_provider_chore import is_authorized
from backend.db.models.hosts_model import HostsModel
from backend.schemas.containers_schema import (
    ContainerGetResponseBody,
    ContainerPatchRequestBody,
    ContainersListItem,
)
from backend.db.session import get_async_session
from backend.db.models import ContainersModel
from backend.db.util import (
    insert_or_update_container,
    ContainerInsertOrUpdateData,
)
from backend.core import (
    HostsManager,
    ALL_CONTAINERS_STATUS_KEY,
    get_host_cache_key,
    get_group_cache_key,
    GroupCheckProgressCache,
    HostCheckProgressCache,
    AllCheckProgressCache,
    ProcessCache,
)
from backend.core.containers_core import (
    check_all,
    check_host,
    check_group,
)
from backend.core.container.container_group import (
    get_container_group,
)
from shared.schemas.container_schemas import (
    GetContainerListBodySchema,
)
from .util import map_container_schema, get_host, get_host_containers

router = APIRouter(
    prefix="/containers",
    tags=["containers"],
    dependencies=[Depends(is_authorized)],
)


def _raise_for_host_status(host: HostsModel):
    """Raise an error if host disabled"""
    if not host.enabled:
        raise HTTPException(409, "Host disabled")


@router.get(
    path="/{host_id}/list",
    response_model=list[ContainersListItem],
    description="Get list of containers for docker host",
)
async def containers_list(
    host_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> list[ContainersListItem]:
    host = await get_host(host_id, session)
    _raise_for_host_status(host)
    client = HostsManager.get_host_client(host)
    containers = await client.container.list(
        GetContainerListBodySchema(all=True)
    )
    result = await session.execute(
        select(ContainersModel).where(
            ContainersModel.host_id == host_id
        )
    )
    containers_db = result.scalars().all()
    _list: list[ContainersListItem] = []
    for c in containers:
        _db_item = next(
            (item for item in containers_db if item.name == c.name),
            None,
        )
        _item = map_container_schema(host_id, c, _db_item)
        _list.append(_item)
    return _list


@router.get(
    path="/{host_id}/{container_name_or_id}",
    description="Get container info (inspect)",
    response_model=ContainerGetResponseBody,
)
async def get_container(
    host_id: int,
    container_name_or_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> ContainerGetResponseBody:
    host = await get_host(host_id, session)
    _raise_for_host_status(host)
    client = HostsManager.get_host_client(host)
    inspect = await client.container.inspect(container_name_or_id)
    stmt = (
        select(ContainersModel)
        .where(
            ContainersModel.host_id == host_id,
            ContainersModel.name == inspect.name,
        )
        .limit(1)
    )
    result = await session.execute(stmt)
    db_item = result.scalar_one_or_none()
    return ContainerGetResponseBody(
        item=map_container_schema(
            host_id,
            inspect,
            db_item,
        ),
        inspect=inspect,
    )


@router.patch(
    path="/{host_id}/{c_name}",
    description="Patch container data (create db entry if not exists)",
    response_model=ContainersListItem,
)
async def patch_container_data(
    host_id: int,
    c_name: str,
    body: ContainerPatchRequestBody,
    session: AsyncSession = Depends(get_async_session),
) -> ContainersListItem:
    db_cont = await insert_or_update_container(
        session,
        host_id,
        c_name,
        ContainerInsertOrUpdateData(
            **body.model_dump(exclude_unset=True)
        ),
    )
    host = await get_host(host_id, session)
    _raise_for_host_status(host)
    client = HostsManager.get_host_client(host)
    d_cont = await client.container.inspect(db_cont.name)
    return map_container_schema(host_id, d_cont, db_cont)


@router.post(
    path="/check",
    description="Run general check process. Returns ID of the task that can be used for monitoring.",
)
async def check_all_ep(update: bool = False):
    asyncio.create_task(check_all(update))
    return ALL_CONTAINERS_STATUS_KEY


@router.post(
    path="/check/{host_id}",
    description="Check specific host. Returns ID of the task that can be used for monitoring.",
)
async def check_host_ep(
    host_id: int,
    update: bool = False,
    session: AsyncSession = Depends(get_async_session),
) -> str:
    host = await get_host(host_id, session)
    _raise_for_host_status(host)
    containers = await get_host_containers(session, host_id)
    client = HostsManager.get_host_client(host)
    _ = asyncio.create_task(
        check_host(host, client, update, containers),
    )
    return get_host_cache_key(host)


@router.post(
    path="/check/{host_id}/{c_name}",
    description="Check specific container. Returns ID of the task that can be used for monitoring.",
)
async def check_container_ep(
    host_id: int,
    c_name: str,
    update: bool = False,
    session: AsyncSession = Depends(get_async_session),
) -> str:
    host = await get_host(host_id, session)
    _raise_for_host_status(host)
    client = HostsManager.get_host_client(host)
    if not await client.container.exists(c_name):
        raise HTTPException(404, "Container not found")
    container = await client.container.inspect(c_name)
    containers = await client.container.list(
        GetContainerListBodySchema(all=True)
    )
    db_containers = await get_host_containers(session, host_id)
    group = get_container_group(
        container, containers, db_containers, update
    )
    _ = asyncio.create_task(check_group(client, host, group, update))
    return get_group_cache_key(host, group)


@router.get(
    path="/progress",
    description="Get progress of general check",
    response_model=AllCheckProgressCache
    | HostCheckProgressCache
    | GroupCheckProgressCache
    | None,
)
def progress(
    cache_id: str,
) -> AllCheckProgressCache | HostCheckProgressCache | GroupCheckProgressCache | None:
    CACHE = ProcessCache(cache_id)
    return CACHE.get()