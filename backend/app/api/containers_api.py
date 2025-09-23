import asyncio
import logging
from typing import cast
from docker.models.containers import Container
from fastapi import APIRouter, Depends
import docker
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth_core import is_authorized
from app.config import Config
from app.schemas.containers_schema import (
    ContainerPatchRequestBody,
    ContainerGetResponseBody,
)
from app.db.models.settings_model import SettingModel
from app.db.models.containers_model import ContainersModel
from app.db.session import get_async_session
from app.core.containers_core import (
    CheckStatusDict,
    check_and_update_containers,
    get_check_status,
    STATUS_CACHE_KEY,
)
from app.helpers import is_self_container

client = docker.from_env()
router = APIRouter(
    prefix="/containers", tags=["containers"], dependencies=[Depends(is_authorized)]
)


@router.get(path="/list", response_model=list[ContainerGetResponseBody])
async def containers_list(
    session: AsyncSession = Depends(get_async_session),
):
    containers: list[Container] = client.containers.list(all=True)
    _list: list[ContainerGetResponseBody] = []
    for c in containers:
        name = str(c.name)
        _item = ContainerGetResponseBody(
            name=name,
            short_id=c.short_id,
            ports=c.ports,
            status=c.attrs["State"]["Status"],
            health=str(c.health),
            is_self=is_self_container(c),
        )

        stmt = select(ContainersModel).where(ContainersModel.name == name).limit(1)
        result = await session.execute(stmt)
        _dbItem = result.scalar_one_or_none()
        if _dbItem:
            _item.check_enabled = _dbItem.check_enabled
            _item.update_enabled = _dbItem.update_enabled

        _list.append(_item)
    return _list


@router.patch(
    path="/{name}",
    description="Patch container data (create db entry if not exists)",
)
async def patch_container_data(
    name: str,
    body: ContainerPatchRequestBody,
    session: AsyncSession = Depends(get_async_session),
):
    stmt = select(ContainersModel).where(ContainersModel.name == name).limit(1)
    result = await session.execute(stmt)
    container = result.scalar_one_or_none()
    if container:
        for key, value in body.model_dump(exclude_unset=True).items():
            if getattr(container, key) != value:
                setattr(container, key, value)
        await session.commit()
        await session.refresh(container)
        return container
    else:
        new_container = ContainersModel(**body.model_dump(), name=name)
        session.add(new_container)
        await session.commit()
        await session.refresh(new_container)
        return new_container


@router.post(
    path="/check_and_update",
    description="Run check and update now. Returns ID of the task that can be used for monitoring.",
)
async def check_all():
    task = asyncio.create_task(check_and_update_containers())
    return STATUS_CACHE_KEY


@router.get(
    path="/check_progress/{id}",
    description="Get progress of check and update process",
    response_model=CheckStatusDict,
)
def check_progress(id: str) -> CheckStatusDict | None:
    return get_check_status(id)
