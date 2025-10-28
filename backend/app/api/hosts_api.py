import asyncio
from fastapi import APIRouter, Depends, HTTPException, Response
from python_on_whales import DockerException
import requests
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core import is_authorized, HostsManager
from backend.app.schemas import (
    HostInfo,
    HostBase,
    HostStatusResponseBody,
)
from backend.app.db.session import get_async_session
from backend.app.db.models import HostsModel
from backend.app.api.util import get_host
from backend.app.helpers.asyncall import asyncall

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
        HostStatusResponseBody(id=id)
    client = HostsManager.get_host_client(host)
    try:
        _ = await asyncall(client.public.health)
        _ = await asyncall(client.public.access)
        return HostStatusResponseBody(id=id, ok=True)
    except requests.exceptions.HTTPError as e:
        return HostStatusResponseBody(
            id=id,
            ok=False,
            err=str(e),
        )
    except asyncio.TimeoutError as e:
        return HostStatusResponseBody(
            id=id,
            ok=False,
            err="Timeout error",
        )
    except Exception as e:
        return HostStatusResponseBody(
            id=id,
            ok=False,
            err="Unknown error",
        )
