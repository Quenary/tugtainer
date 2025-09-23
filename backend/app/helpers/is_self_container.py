from docker.models.containers import Container
from app.config import Config

SELF_CONTAINER_ID: str | None = None


def _read_container_id_from_cpuset() -> str | None:
    """Read Container ID from /proc/1/cpuset"""
    try:
        with open("/proc/1/cpuset") as f:
            path = f.read().strip()
            if path and "/" in path:
                return path.split("/")[-1]
    except FileNotFoundError:
        pass
    return None


def _read_container_id_from_cgroup() -> str | None:
    """Read Container ID from /proc/self/cgroup (cgroup v2 support)."""
    try:
        with open("/proc/self/cgroup") as f:
            for line in f:
                parts = line.strip().split(":")
                if len(parts) == 3 and "/" in parts[2]:
                    candidate = parts[2].split("/")[-1]
                    if len(candidate) >= 12:  # minimum for short_id
                        return candidate
    except FileNotFoundError:
        pass
    return None


def _get_self_container_id() -> str | None:
    global SELF_CONTAINER_ID
    if SELF_CONTAINER_ID is not None:
        return SELF_CONTAINER_ID

    cid = _read_container_id_from_cpuset()
    if not cid:
        cid = _read_container_id_from_cgroup()
    if not cid:
        cid = Config.HOSTNAME

    SELF_CONTAINER_ID = cid
    return SELF_CONTAINER_ID


def is_self_container(container: Container) -> bool:
    """
    Check if provided container is self container
    """
    cid = _get_self_container_id()
    id = container.id or container.short_id or ""
    return bool(cid and cid.startswith(id))
