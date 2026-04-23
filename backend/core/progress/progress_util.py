import uuid
from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from backend.core.progress.progress_cache import ProgressCache
from backend.core.progress.progress_schemas import (
    ActionProgress,
)
from backend.core.update_actions.update_actions_schema import (
    UpdatePlan,
)
from backend.enums.action_status_enum import EActionStatus
from backend.modules.hosts.hosts_model import HostsModel

ALL_CONTAINERS_STATUS_KEY = str(uuid.uuid4())


def get_host_cache_key(host: HostsModel) -> str:
    return f"{host.id}:{host.name}"


def get_plan_cache_key(host: HostsModel, plan: UpdatePlan) -> str:
    return f"{get_host_cache_key(host)}:{sorted(plan.to_update)}"


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
