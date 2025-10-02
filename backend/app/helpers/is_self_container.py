from docker.models.containers import Container
from app.config import Config
import re
import logging

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
                # /var/lib/docker/overlay2/<id>/...
                match = re.search(r"/overlay2/([0-9a-f]{64})/", line)
                if match:
                    return match.group(1)
    except Exception as e:
        logging.warning(
            f"Error reading self container ID from /proc/1/mountinfo, {e}"
        )
    return None


def _get_self_container_id() -> str | None:
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
    self_id = _get_self_container_id() or ""
    c_id = container.short_id or container.id or ""
    if c_id and self_id and self_id.startswith(c_id):
        return True
    c_hostname = container.attrs.get("Config", {}).get("Hostname", "")
    if (
        c_hostname
        and Config.HOSTNAME
        and c_hostname == Config.HOSTNAME
    ):
        return True
    return False
