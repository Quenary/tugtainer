import asyncio
from docker.models.containers import Container
from fastapi import APIRouter, Depends
import docker
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
    check_and_update_containers,
    get_check_status,
    STATUS_CACHE_KEY,
)
from app.helpers import is_self_container
from .util import map_container_schema

client = docker.from_env()
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
    containers: list[Container] = client.containers.list(all=True)
    _list: list[ContainerGetResponseBody] = []
    for c in containers:
        stmt = (
            select(ContainersModel)
            .where(ContainersModel.name == str(c.name))
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
    d_cont = client.containers.get(db_cont.name)
    return map_container_schema(d_cont, db_cont)


@router.post(
    path="/update_all",
    description="Run check and update now. Returns ID of the task that can be used for monitoring.",
)
async def update_all():
    asyncio.create_task(check_and_update_containers())
    return STATUS_CACHE_KEY


@router.get(
    path="/check_progress/{id}",
    description="Get progress of check and update process",
    response_model=CheckStatusDict,
)
def check_progress(id: str) -> CheckStatusDict | None:
    return get_check_status(id)
