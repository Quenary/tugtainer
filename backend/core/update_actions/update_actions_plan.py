from collections.abc import Sequence
from typing import cast

from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from sqlalchemy import select

from backend.const import (
    DOCKER_COMPOSE_DEPENDS_ON_LABEL,
    TUGTAINER_DEPENDS_ON_LABEL,
)
from backend.core.container_util.get_service_name import get_service_name
from backend.core.container_util.is_protected_container import is_protected_container
from backend.core.container_util.is_running_container import is_running_container
from backend.core.update_actions.update_actions_schema import (
    UpdatePlan,
)
from backend.db.session import async_session_maker
from backend.modules.containers.containers_model import (
    ContainersModel,
)
from backend.modules.hosts.hosts_model import HostsModel
from backend.modules.settings.settings_enum import ESettingKey
from backend.modules.settings.settings_storage import SettingsStorage

from .update_actions_util import get_compose_id, get_dependencies


async def build_update_plan(
    host: HostsModel,
    containers: Sequence[ContainerInspectResult],
    manual_for: Sequence[ContainerInspectResult] = [],
) -> UpdatePlan:
    """
    Get update plan for the given containers.
    :param host: host data
    :param containers: containers to process
    :param manual_for: override updatable containers (for manual runs)
    """
    update_only_running = SettingsStorage.get(ESettingKey.UPDATE_ONLY_RUNNING)
    async with async_session_maker() as session:
        containers_db = {
            c.name: c
            for c in (
                await session.execute(
                    select(ContainersModel).where(ContainersModel.host_id == host.id)
                )
            )
            .scalars()
            .all()
        }

    # Filter potentially updatable/affected
    containers = [
        c
        for c in containers
        if not is_protected_container(c)
        and (is_running_container(c) or not update_only_running)
    ]

    to_update: set[str] = set()
    if manual_for:
        for c in manual_for:
            c_name = cast(str, c.name)
            c_db = containers_db.get(c_name)
            if c_db and c_db.update_available:
                to_update.add(c_name)
    else:
        for c in containers:
            c_name = cast(str, c.name)
            c_db = containers_db.get(c_name)
            if c_db and c_db.update_available and c_db.update_enabled:
                to_update.add(c_name)

    # region Dependency graphs
    compose_service_names: dict[
        str, dict[str, str]
    ] = {}  # Map of service name to container name per compose
    depends_on_map: dict[str, set[str]] = {}  # Container to dependencies
    dependables_map: dict[str, set[str]] = {}  # Container to dependables (reverse)

    for c in containers:
        c_name = cast(str, c.name)
        srvn = get_service_name(c)
        compose_id = get_compose_id(c)
        if srvn and compose_id:
            if not isinstance(compose_service_names.get(compose_id), dict):
                compose_service_names[compose_id] = {}
            compose_service_names[compose_id][srvn] = c_name

    for c in containers:
        c_name = cast(str, c.name)
        depends_on_map[c_name] = get_dependencies(c, TUGTAINER_DEPENDS_ON_LABEL)

        compose_id = get_compose_id(c)

        if compose_id:
            neighbors = compose_service_names.get(compose_id, {})
            for d in get_dependencies(c, DOCKER_COMPOSE_DEPENDS_ON_LABEL):
                if d_name := neighbors.get(d):
                    depends_on_map[c_name].add(d_name)

    for name, deps in depends_on_map.items():
        for dep in deps:
            if not isinstance(dependables_map.get(dep), set):
                dependables_map[dep] = set()
            dependables_map[dep].add(name)
    # endregion

    # region Affected (BFS over dependables_map)
    affected: set[str] = set()
    queue: list[str] = list(to_update)

    while queue:
        node = queue.pop(0)
        if node in affected:
            continue

        if node not in to_update:
            affected.add(node)

        for dep in dependables_map.get(node, set()):
            if dep not in affected:
                queue.append(dep)
    # endregion

    # region Topological sort
    visited: set[str] = set()
    order: list[str] = []

    def dfs(node: str):
        if node in visited:
            return
        visited.add(node)

        for dep in depends_on_map.get(node, set()):
            dfs(dep)

        order.append(node)

    for n in affected | to_update:
        dfs(n)
    # endregion

    # filter only existing
    all_names = {c.name for c in containers}
    to_update &= all_names
    affected &= all_names
    order = [item for item in order if item in all_names]

    return UpdatePlan(
        to_update=to_update,
        affected=affected,
        order=order,
    )
