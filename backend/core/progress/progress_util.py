import uuid

from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from backend.core.container_group.container_group_schemas import (
    ContainerGroup,
)
from backend.core.progress.progress_cache import ProgressCache
from backend.core.progress.progress_schemas import (
    ActionProgress,
)
from backend.enums.action_status_enum import EActionStatus
from backend.modules.hosts.hosts_model import HostsModel

ALL_CONTAINERS_STATUS_KEY = str(uuid.uuid4())


def get_host_cache_key(host: HostsModel) -> str:
    return f"{host.id}:{host.name}"


def get_group_cache_key(
    host: HostsModel, group: ContainerGroup
) -> str:
    return f"{get_host_cache_key(host)}:{group.name}"


def get_container_cache_key(
    host: HostsModel, container: ContainerInspectResult
) -> str:
    return f"{get_host_cache_key(host)}:{container.name}"


def is_allowed_start_cache(
    cache: ActionProgress | None,
) -> bool:
    """Whether action allowed to start with current cache status"""
    return bool(
        not cache
        or cache.get("status")
        in [EActionStatus.DONE, EActionStatus.ERROR]
    )
