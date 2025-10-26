from python_on_whales import Container
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import Config
import re
import logging
from app.core.hosts_manager import HostsManager
from app.db.models import ContainersModel
from app.db.session import async_session_maker
from .asyncall import asyncall
from .now import now

HEX64_RE = r"([0-9a-f]{64})"
HEX12_RE = r"([0-9a-f]{12})"
SELF_CONTAINER_ID: str | None = None


def _read_container_id_from_cpuset() -> str | None:
    """Read Container ID from /proc/1/cpuset using regexp"""
    try:
        with open("/proc/1/cpuset") as f:
            data = f.read().strip()
            match = re.search(HEX64_RE, data)
            if not match:
                match = re.search(HEX12_RE, data)
            if match:
                return match.group(1)
    except Exception as e:
        logging.warning(
            f"Error reading self container ID from /proc/1/cpuset, {e}"
        )
    return None


def _read_container_id_from_cgroup() -> str | None:
    """Read Container ID from /proc/self/cgroup using regexp (cgroup v1/v2)."""
    try:
        with open("/proc/self/cgroup") as f:
            for line in f:
                match = re.search(HEX64_RE, line)
                if not match:
                    match = re.search(HEX12_RE, line)
                if match:
                    return match.group(1)
    except Exception as e:
        logging.warning(
            f"Error reading self container ID from /proc/self/cgroup, {e}"
        )
    return None


def _read_container_id_from_mountinfo() -> str | None:
    """Read Container ID from /proc/1/mountinfo"""
    try:
        with open("/proc/1/mountinfo") as f:
            for line in f:
                # /var/lib/docker/containers/<id>/...
                match = re.search(
                    r"/containers/([0-9a-f]{64})/", line
                )
                if match:
                    return match.group(1)
    except Exception as e:
        logging.warning(
            f"Error reading self container ID from /proc/1/mountinfo, {e}"
        )
    return None


def get_self_container_id() -> str | None:
    global SELF_CONTAINER_ID
    if SELF_CONTAINER_ID is not None:
        return SELF_CONTAINER_ID

    for fn in (
        _read_container_id_from_cpuset,
        _read_container_id_from_cgroup,
        _read_container_id_from_mountinfo,
    ):
        cid = fn()
        if cid:
            SELF_CONTAINER_ID = cid
            return cid

    return SELF_CONTAINER_ID


def is_self_container(container: Container) -> bool:
    """
    Check if provided container is self container
    """
    self_id = get_self_container_id() or ""
    c_id = container.id[0:12]
    if c_id and self_id and self_id.startswith(c_id):
        return True
    c_hostname = container.config.hostname
    if (
        c_hostname
        and Config.HOSTNAME
        and c_hostname == Config.HOSTNAME
    ):
        return True
    return False


async def get_self_container(
    session: AsyncSession,
) -> tuple[Container, ContainersModel | None] | None:
    """
    Get self container
    :returns: container object and container db data (if exists)
    """
    self_container_id = get_self_container_id()
    if not self_container_id:
        return None
    clients = HostsManager.get_all()
    for clid, cli in clients:
        try:
            if await asyncall(
                lambda: cli.container.exists(self_container_id)
            ):
                cont = await asyncall(
                    lambda: cli.container.inspect(self_container_id)
                )
                stmt = (
                    select(ContainersModel)
                    .where(
                        and_(
                            ContainersModel.host_id == clid,
                            ContainersModel.name == cont.name,
                        )
                    )
                    .limit(1)
                )
                result = await session.execute(stmt)
                db_cont = result.scalar_one_or_none()
                return (cont, db_cont)
        except Exception as e:
            logging.exception(e)
            logging.error(
                f"Failed to get self container object from client {clid}"
            )
            pass
    return None


async def clear_self_container_update_available():
    """
    Clear self container update available flag in db.
    Assuming that each self container start happens after an image update,
    this is the simplest way to avoid incorrent notification about an available update.
    """
    try:
        async with async_session_maker() as session:
            res = await get_self_container(session)
            if not res:
                return
            _, c_db = res
            if not c_db:
                return
            logging.info(
                "Clearing self container update available flag"
            )
            c_db.update_available = False
            c_db.checked_at = now()
            await session.commit()
    except Exception as e:
        logging.exception(e)
        logging.error(
            "Failed to clear self container update available flag"
        )
