import asyncio
from collections.abc import Awaitable, Callable
from typing import Any, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, status
from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import Config
from backend.core.agent_client import AgentClientManager
from backend.core.container_util.is_protected_container import is_protected_container
from backend.core.jobs.check.check_all import check_all_hosts
from backend.core.jobs.jobs_cache import JobStateCache
from backend.core.jobs.jobs_coordinator import host_job_coordinator
from backend.core.jobs.jobs_schemas import AllHostsState, HostState, JobKind
from backend.core.jobs.jobs_util import ALL_HOSTS_CACHE_KEY, get_host_cache_key
from backend.core.jobs.update.update_all import update_all_hosts
from backend.db.session import get_async_session
from backend.modules.auth.auth_util import is_authorized
from backend.modules.hosts.hosts_model import HostsModel
from backend.modules.hosts.hosts_util import get_host
from shared.schemas.container_schemas import (
    GetContainerListBodySchema,
    GetContainerLogsRequestBody,
)

from .containers_model import ContainersModel
from .containers_schemas import (
    ContainerGetResponseBody,
    ContainerNamesRequestBody,
    ContainerPatchRequestBody,
    ContainersListItem,
)
from .containers_util import (
    ContainerInsertOrUpdateData,
    insert_or_update_container,
)

containers_router = APIRouter(
    prefix="/containers",
    tags=["containers"],
    dependencies=[Depends(is_authorized)],
)


def _raise_for_host_status(host: HostsModel):
    """Raise an error if host disabled"""
    if not host.enabled:
        raise HTTPException(409, "Host disabled")


def _raise_for_protected_container(container: ContainerInspectResult):
    """Raise an error if container is protected"""
    if is_protected_container(container):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Protected container not allowed",
        )


@containers_router.get(
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
    client = AgentClientManager.get_host_client(host)
    containers = await client.container.list(GetContainerListBodySchema(all=True))
    result = await session.execute(
        select(ContainersModel).where(ContainersModel.host_id == host_id)
    )
    containers_db = result.scalars().all()
    _list: list[ContainersListItem] = []
    for c in containers:
        _db_item = next(
            (item for item in containers_db if item.name == c.name),
            None,
        )
        _item = ContainersListItem.from_sources(host_id, c, _db_item)
        _list.append(_item)
    return _list


@containers_router.get(
    path="/progress/{host_id}",
    description="Get unified check/update job state for a host",
    response_model=HostState | None,
)
async def host_progress(
    host_id: int,
    session: AsyncSession = Depends(get_async_session),
) -> HostState | None:
    host = await get_host(host_id, session)
    return JobStateCache[HostState](get_host_cache_key(host)).get()


@containers_router.get(
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
    client = AgentClientManager.get_host_client(host)
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
        item=ContainersListItem.from_sources(
            host_id,
            inspect,
            db_item,
        ),
        inspect=inspect,
    )


@containers_router.patch(
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
    if body.hooks is not None and not Config.ALLOW_HOOKS:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Hooks are disabled. Set ALLOW_HOOKS=true on the backend to enable them.",
        )
    db_cont = await insert_or_update_container(
        session,
        host_id,
        c_name,
        ContainerInsertOrUpdateData(
            **cast(ContainerInsertOrUpdateData, body.model_dump(exclude_unset=True))
        ),
    )
    host = await get_host(host_id, session)
    _raise_for_host_status(host)
    client = AgentClientManager.get_host_client(host)
    d_cont = await client.container.inspect(db_cont.name)
    return ContainersListItem.from_sources(host_id, d_cont, db_cont)


@containers_router.get(
    path="/hooks_enabled",
    description="Check if container hooks are enabled (ALLOW_HOOKS env var)",
    response_model=bool,
)
async def hooks_enabled() -> bool:
    return Config.ALLOW_HOOKS


async def _enqueue_host_job(
    host: HostsModel,
    kind: JobKind,
    names: list[str] | None,
) -> str:
    _raise_for_host_status(host)
    resolved = names if names else None
    if resolved:
        client = AgentClientManager.get_host_client(host)
        containers = await client.container.list(GetContainerListBodySchema(all=True))
        existing = {c.name for c in containers}
        found = [n for n in resolved if n in existing]
        if not found:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Container not found")
        resolved = found
    await host_job_coordinator.submit(
        host,
        kind,
        names=resolved,
        manual=True,
        wait=False,
    )
    return get_host_cache_key(host)


@containers_router.post(
    path="/check",
    description="Run general check process. Returns ID of the task that can be used for monitoring.",
)
async def check_all():
    asyncio.create_task(check_all_hosts(True))
    return ALL_HOSTS_CACHE_KEY


@containers_router.post(
    path="/check/{host_id}",
    description="Check host containers. Optional body.names limits the set. Returns host progress cache id.",
)
async def check_host(
    host_id: int,
    body: ContainerNamesRequestBody | None = None,
    session: AsyncSession = Depends(get_async_session),
) -> str:
    host = await get_host(host_id, session)
    names = body.names if body and body.names else None
    return await _enqueue_host_job(host, "check", names)


@containers_router.post(
    path="/check/{host_id}/{c_name}",
    description="Check specific container. Returns host progress cache id.",
)
async def check_container(
    host_id: int,
    c_name: str,
    session: AsyncSession = Depends(get_async_session),
) -> str:
    host = await get_host(host_id, session)
    return await _enqueue_host_job(host, "check", [c_name])


@containers_router.post(
    path="/update",
    description="Run general update process. Returns ID of the task that can be used for monitoring.",
)
async def update_all():
    asyncio.create_task(update_all_hosts())
    return ALL_HOSTS_CACHE_KEY


@containers_router.post(
    path="/update/{host_id}",
    description="Update host containers. Optional body.names limits the set. Returns host progress cache id.",
)
async def update_host(
    host_id: int,
    body: ContainerNamesRequestBody | None = None,
    session: AsyncSession = Depends(get_async_session),
) -> str:
    host = await get_host(host_id, session)
    names = body.names if body and body.names else None
    return await _enqueue_host_job(host, "update", names)


@containers_router.post(
    path="/update/{host_id}/{c_name}",
    description="Update specific container. Returns host progress cache id.",
)
async def update_container(
    host_id: int,
    c_name: str,
    session: AsyncSession = Depends(get_async_session),
) -> str:
    host = await get_host(host_id, session)
    return await _enqueue_host_job(host, "update", [c_name])


@containers_router.get(
    path="/progress",
    description="Get progress by cache id (host key or global 'all')",
    response_model=AllHostsState | HostState | None,
)
def progress(
    cache_id: str,
) -> AllHostsState | HostState | None:
    CACHE = JobStateCache[Any](cache_id)
    return CACHE.get()


@containers_router.post(
    path="/{host_id}/logs/{container_name_or_id}",
    description="Get log of container",
    response_model=str,
)
async def logs(
    host_id: int,
    container_name_or_id: str,
    body: GetContainerLogsRequestBody,
    session: AsyncSession = Depends(get_async_session),
) -> str:
    host = await get_host(host_id, session)
    _raise_for_host_status(host)

    client = AgentClientManager.get_host_client(host)
    return await client.container.logs(
        container_name_or_id,
        body,
    )


ControlContainerCommand = Literal[
    "start", "stop", "restart", "kill", "pause", "unpause"
]


@containers_router.post(
    path="/{host_id}/{command}/{container_name_or_id}",
    description="Control container state with basic commands",
    response_model=ContainerGetResponseBody,
)
async def control_container(
    host_id: int,
    command: ControlContainerCommand,
    container_name_or_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    host = await get_host(host_id, session)
    _raise_for_host_status(host)

    client = AgentClientManager.get_host_client(host)
    inspect = await client.container.inspect(container_name_or_id)
    _raise_for_protected_container(inspect)

    _command: Callable[[str], Awaitable[Any]] = getattr(client.container, command)
    if not asyncio.iscoroutinefunction(_command):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Command not allowed")
    await _command(container_name_or_id)

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
        item=ContainersListItem.from_sources(
            host_id,
            inspect,
            db_item,
        ),
        inspect=inspect,
    )
