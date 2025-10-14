import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth_core import is_authorized
from app.schemas.containers_schema import (
    ContainerPatchRequestBody,
    ContainerGetResponseBody,
)
from app.db import (
    get_async_session,
    ContainersModel,
    insert_or_update_container,
    ContainerInsertOrUpdateData,
)
from app.core import (
    HostsManager,
    get_host_cache_key,
    get_container_cache_key,
    ContainerCheckData,
    HostCheckData,
    AllCheckData,
    ProcessCache,
    ALL_CONTAINERS_STATUS_KEY,
)
from app.core.containers_core import (
    check_all,
    check_host,
    check_container,
)
from app.helpers import get_self_container_id
from .util import map_container_schema
from python_on_whales import Container
from app.api.util import get_host
import logging

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
    containers: list[Container] = client.container.list(all=True)
    stmt = select(ContainersModel).where(
        ContainersModel.host_id == host_id
    )
    result = await session.execute(stmt)
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
    d_cont = client.container.inspect(db_cont.name)
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
    client = HostsManager.get_host_client(host)
    asyncio.create_task(check_host(host, client, update))
    return get_host_cache_key(host.id)


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
    asyncio.create_task(check_container(client, host, c_name, update))
    return get_container_cache_key(host_id, c_name)


@router.get(
    path="/progress/{cache_id}",
    description="Get progress of general check",
    response_model=AllCheckData
    | HostCheckData
    | ContainerCheckData
    | None,
)
def progress(
    cache_id: str,
) -> AllCheckData | HostCheckData | ContainerCheckData | None:
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
    self_container_id = get_self_container_id()
    if not self_container_id:
        return False
    clients = HostsManager.get_all()
    for clid, cli in clients:
        try:
            if cli.container.exists(self_container_id):
                cont = cli.container.inspect(self_container_id)
                name = cont.name
                stmt = (
                    select(ContainersModel)
                    .where(
                        and_(
                            ContainersModel.host_id == clid,
                            ContainersModel.name == name,
                        )
                    )
                    .limit(1)
                )
                result = await session.execute(stmt)
                db_cont = result.scalar_one_or_none()
                if not db_cont:
                    return False
                return db_cont.update_available
        except Exception as e:
            logging.error(
                "Error while getting self container update value"
            )
            logging.exception(e)
    return False
