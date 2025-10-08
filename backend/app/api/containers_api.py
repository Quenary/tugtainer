import asyncio
from fastapi import APIRouter, Depends
from sqlalchemy import select
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
)
from app.core.containers_core import (
    CheckStatusDict,
    check_and_update_all_containers,
    check_container,
    get_check_status,
    _ALL_CONTAINERS_STATUS_KEY,
)
from app.helpers import is_self_container
from .util import map_container_schema
from python_on_whales import docker
from python_on_whales import Container

# _client = docker.from_env()
router = APIRouter(
    prefix="/containers",
    tags=["containers"],
    dependencies=[Depends(is_authorized)],
)


@router.get(
    path="/list", response_model=list[ContainerGetResponseBody]
)
async def containers_list(
    session: AsyncSession = Depends(get_async_session),
) -> list[ContainerGetResponseBody]:
    containers: list[Container] = docker.container.list(all=True)
    _list: list[ContainerGetResponseBody] = []
    for c in containers:
        stmt = (
            select(ContainersModel)
            .where(ContainersModel.name == c.name)
            .limit(1)
        )
        result = await session.execute(stmt)
        _dbItem = result.scalar_one_or_none()
        _item = map_container_schema(c, _dbItem)
        _list.append(_item)
    return _list


@router.patch(
    path="/{name}",
    description="Patch container data (create db entry if not exists)",
    response_model=ContainerGetResponseBody,
)
async def patch_container_data(
    name: str,
    body: ContainerPatchRequestBody,
    session: AsyncSession = Depends(get_async_session),
) -> ContainerGetResponseBody:
    db_cont = await insert_or_update_container(
        session, name, body.model_dump(exclude_unset=True)
    )
    d_cont = docker.container.inspect(db_cont.name)
    return map_container_schema(d_cont, db_cont)


@router.post(
    path="/check/all",
    description="Run check and update now. Returns ID of the task that can be used for monitoring.",
)
async def update_all():
    asyncio.create_task(check_and_update_all_containers())
    return _ALL_CONTAINERS_STATUS_KEY


@router.post(
    path="/check/{name}",
    description="Check specific container. Returns ID of the task that can be used for monitoring.",
)
async def check_container_ep(name: str) -> str:
    asyncio.create_task(check_container(name))
    return name


@router.post(
    path="/update/{name}",
    description="Check and update specific container. Returns ID of the task that can be used for monitoring.",
)
async def update_container(name: str) -> str:
    asyncio.create_task(check_container(name, True))
    return name


@router.get(
    path="/check_progress/{id}",
    description="Get progress of check and update process",
    response_model=CheckStatusDict,
)
def check_progress(id: str) -> CheckStatusDict | None:
    return get_check_status(id)


@router.get(
    path="/update_available/self",
    description="Get new version availability for self container",
    response_model=bool,
)
async def is_update_available_self(
    session: AsyncSession = Depends(get_async_session),
):
    containers: list[Container] = docker.container.list()
    self_c = [item for item in containers if is_self_container(item)]
    if not self_c:
        return False
    stmt = select(ContainersModel.update_available).where(
        ContainersModel.name == self_c[0].name
    )
    result = await session.execute(stmt)
    update_available = result.scalar_one_or_none()
    return bool(update_available)
