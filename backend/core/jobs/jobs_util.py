from collections.abc import Mapping

from backend.enums.job_status_enum import EJobStatus
from backend.modules.hosts.hosts_model import HostsModel

ALL_HOSTS_CACHE_KEY = "all"


def get_host_cache_key(host: HostsModel) -> str:
    return f"{host.id}:{host.name}"


def is_allowed_start(state: Mapping[str, object] | None) -> bool:
    """Whether a global job may start given the current cache status."""
    return bool(
        not state
        or state.get("status") in [EJobStatus.DONE, EJobStatus.ERROR]
    )
