from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import is_authorized, HostManager
from app.schemas import HostInfo, HostBase
from app.db import get_async_session, HostModel
from app.api.util import get_host

router = APIRouter(
    prefix="/host",
    tags=["host"],
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
    stmt = select(HostModel)
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
        select(HostModel).where(HostModel.name == body.name).limit(1)
    )
    result = await session.execute(stmt)
    host = result.scalar_one_or_none()
    if host:
        raise HTTPException(400, "Host name is already taken")
    _body = body.model_dump(exclude_unset=True)
    new_host = HostModel(**_body)
    session.add(new_host)
    await session.commit()
    await session.refresh(new_host)
    HostManager.set_client(new_host)
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
    return get_host(id, session)


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
    HostManager.set_client(host)
    return host

@router.delete(
    path="/{id}",
    description="Delete host"
)
async def delete(
    id: int,
    session: AsyncSession = Depends(get_async_session),
):
    host = await get_host(id, session)
    HostManager.remove_client(host)
    await session.delete(host)
    await session.commit()
    return {"detail": "Host deleted successfully"}
