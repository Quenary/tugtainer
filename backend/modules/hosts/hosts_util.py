import logging

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import Config
from backend.const import LOCAL_AGENT_URL
from backend.db.session import async_session_maker
from backend.exception import TugUrlValidationError, TugUrlValidationSSRFError
from backend.modules.containers.containers_model import ContainersModel
from backend.modules.hosts.hosts_schemas import HostInfo
from backend.util.validate_url_against_ssrf import ResolvedIp, validate_url_against_ssrf

from .hosts_model import HostsModel


async def validate_agent_url_against_ssrf(url: str) -> set[ResolvedIp]:
    """
    Validate agent host URL against SSRF.
    Returns addresses that are safe to pin on the subsequent connection.
    Raises HTTPException with a human-readable English message on failure.
    """
    try:
        return await validate_url_against_ssrf(
            url,
            Config.AGENT_ALLOW_NETWORKS,
            Config.AGENT_ALLOW_ENDPOINTS,
        )
    except TugUrlValidationSSRFError as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"{e}"
            "\nYou can change this behavior through "
            "AGENT_ALLOW_NETWORKS and AGENT_ALLOW_ENDPOINTS "
            "environment variables.",
        ) from e
    except TugUrlValidationError as e:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            str(e),
        ) from e


async def sync_local_agent_secret() -> None:
    """Copy ``AGENT_SECRET`` onto the built-in local host.

    The migration writes the secret once. Later changes of the environment
    variable would otherwise leave the database stale and break signed
    requests. An empty secret is ignored so a missing variable cannot wipe a
    value set in the UI. Nothing is changed when the built-in agent is
    disabled, and hosts with any other URL are left untouched.
    """
    secret = Config.AGENT_SECRET
    if not secret or not Config.AGENT_ENABLED:
        return

    async with async_session_maker() as session:
        stmt = select(HostsModel).where(HostsModel.url == LOCAL_AGENT_URL)
        result = await session.execute(stmt)
        hosts = result.scalars().all()
        changed = False
        for host in hosts:
            if host.secret == secret:
                continue
            host.secret = secret
            changed = True
            logging.info(
                "Synchronized AGENT_SECRET for local agent host %s",
                host.name,
            )
        if changed:
            await session.commit()


async def get_host(host_id: int, session: AsyncSession) -> HostsModel:
    """Get host info from db. Raise 404 if no host found."""
    stmt = select(HostsModel).where(HostsModel.id == host_id).limit(1)
    result = await session.execute(stmt)
    host = result.scalar_one_or_none()
    if not host:
        raise HTTPException(404, "Docker host not found in database")
    return host


async def annotate_available_updates_count(
    hosts: list[HostInfo], session: AsyncSession
) -> None:
    """Populate each host's ``available_updates_count`` ad-hoc attribute.

    The count reflects containers on that host with ``update_available = True``.
    Safe to call with an empty list.
    """
    if not hosts:
        return
    host_ids = [h.id for h in hosts]
    stmt = (
        select(
            ContainersModel.host_id,
            func.count(ContainersModel.id),
        )
        .where(
            ContainersModel.host_id.in_(host_ids),
            ContainersModel.update_available.is_(True),
        )
        .group_by(ContainersModel.host_id)
    )
    result = await session.execute(stmt)
    counts = {host_id: cnt for host_id, cnt in result.all()}

    swarm_host_ids = [h.id for h in hosts if getattr(h, "is_swarm", None) is True]
    if swarm_host_ids:
        from backend.modules.services.services_model import SwarmServicesModel

        svc_stmt = (
            select(
                SwarmServicesModel.host_id,
                func.count(SwarmServicesModel.id),
            )
            .where(
                SwarmServicesModel.host_id.in_(swarm_host_ids),
                SwarmServicesModel.update_available.is_(True),
            )
            .group_by(SwarmServicesModel.host_id)
        )
        svc_result = await session.execute(svc_stmt)
        for host_id, cnt in svc_result.all():
            counts[host_id] = counts.get(host_id, 0) + cnt

    for host in hosts:
        host.available_updates_count = counts.get(host.id, 0)
