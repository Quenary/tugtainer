import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.auth_core import is_authorized
from backend.app.schemas.containers_schema import (
    ContainerPatchRequestBody,
    ContainerGetResponseBody,
)
from backend.app.db.session import get_async_session
from backend.app.db.models import ContainersModel
from backend.app.db.util import (
    insert_or_update_container,
    ContainerInsertOrUpdateData,
)
from backend.app.core import (
    HostsManager,
    ALL_CONTAINERS_STATUS_KEY,
    get_host_cache_key,
    get_group_cache_key,
    GroupCheckData,
    HostCheckData,
    AllCheckData,
    ProcessCache,
)
from backend.app.core.containers_core import (
    check_all,
    check_host,
    check_group,
)
from backend.app.core.container.container_group import get_container_group
from backend.app.core.container.util import update_containers_data_after_check
from backend.app.helpers.self_container import get_self_container
from backend.app.helpers.asyncall import asyncall
from shared.schemas.container_schemas import (
    GetContainerListBodySchema,
)
from .util import map_container_schema, get_host, get_host_containers
from python_on_whales import Container

router = APIRouter(
    prefix="/containers",
    tags=["containers"],
    dependencies=[Depends(is_authorized)],
)


@router.get(
    path="/{host_id}/list",
    response_model=list[ContainerGetResponseBody],
    description="Get list of containers for docker host",
)
async def containers_list(
    host_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> list[ContainerGetResponseBody]:
    host = await get_host(host_id, session)
    if not host.enabled:
        raise HTTPException(409, "Host disabled")
    client = HostsManager.get_host_client(host)
    containers = await asyncall(
        lambda: client.container.list(
            GetContainerListBodySchema(all=True)
        )
    )
    result = await session.execute(
        select(ContainersModel).where(
            ContainersModel.host_id == host_id
        )
    )
    containers_db = result.scalars().all()
    _list: list[ContainerGetResponseBody] = []
    for c in containers:
        _db_item = next(
            (item for item in containers_db if item.name == c.name),
            None,
        )
        _item = map_container_schema(host_id, c, _db_item)
        _list.append(_item)
    return _list


@router.patch(
    path="/{host_id}/{c_name}",
    description="Patch container data (create db entry if not exists)",
    response_model=ContainerGetResponseBody,
)
async def patch_container_data(
    host_id: int,
    c_name: str,
    body: ContainerPatchRequestBody,
    session: AsyncSession = Depends(get_async_session),
) -> ContainerGetResponseBody:
    db_cont = await insert_or_update_container(
        session,
        host_id,
        c_name,
        ContainerInsertOrUpdateData(
            **body.model_dump(exclude_unset=True)
        ),
    )
    host = await get_host(host_id, session)
    client = HostsManager.get_host_client(host)
    d_cont = await asyncall(
        lambda: client.container.inspect(db_cont.name)
    )
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
    containers = await get_host_containers(session, host_id)
    client = HostsManager.get_host_client(host)
    task = asyncio.create_task(
        asyncall(
            lambda: check_host(host, client, update, containers),
            asyncall_timeout=None,
        )
    )
    task.add_done_callback(
        lambda t: asyncio.create_task(
            update_containers_data_after_check(t.result())
        )
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
    client = HostsManager.get_host_client(host)
    if not await asyncall(lambda: client.container.exists(c_name)):
        raise HTTPException(404, "Container not found")
    container = await asyncall(
        lambda: client.container.inspect(c_name)
    )
    containers = await asyncall(
        lambda: client.container.list(
            GetContainerListBodySchema(all=True)
        )
    )
    db_containers = await get_host_containers(session, host_id)
    group = get_container_group(
        container, containers, db_containers, update
    )
    task = asyncio.create_task(
        asyncall(
            lambda: check_group(client, host, group, update),
            asyncall_timeout=None,
        )
    )
    task.add_done_callback(
        lambda t: asyncio.create_task(
            update_containers_data_after_check(t.result())
        )
    )
    return get_group_cache_key(host, group)


@router.get(
    path="/progress/{cache_id}",
    description="Get progress of general check",
    response_model=AllCheckData
    | HostCheckData
    | GroupCheckData
    | None,
)
def progress(
    cache_id: str,
) -> AllCheckData | HostCheckData | GroupCheckData | None:
    CACHE = ProcessCache(cache_id)
    return CACHE.get()


@router.get(
    path="/update_available/self",
    description="Get new version availability for self container",
    response_model=bool,
)
async def is_update_available_self(
    session: AsyncSession = Depends(get_async_session),
):
    res = await get_self_container(session)
    if not res:
        return False
    _, c_db = res
    if not c_db:
        return False
    return c_db.update_available
