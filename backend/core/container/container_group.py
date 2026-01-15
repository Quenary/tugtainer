from dataclasses import dataclass, field
from typing import Literal
from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from python_on_whales.components.image.models import (
    ImageInspectResult,
)
from backend.core.container.schemas.check_result import (
    ContainerCheckResultType,
)
from backend.core.container.util.is_protected_container import (
    is_protected_container,
)
from backend.db.models import ContainersModel
import uuid
from shared.schemas.container_schemas import (
    CreateContainerRequestBodySchema,
)
from backend.const import (
    TUGTAINER_DEPENDS_ON_LABEL,
    DOCKER_COMPOSE_DEPENDS_ON_LABEL,
)
from shared.schemas.manifest_schema import ManifestInspectSchema


@dataclass
class ContainerGroupItem:
    """
    Item of container group to be processed
    :param container: container object
    :param action: action to be performed (selection in db)
    :param available: is new image available
    :param image_spec: image spec e.g. quenary/tugtainer:latest
    :param config: kwargs for create/run
    :param commands: list of commands to be executed after container starts
    :param local_image: local image of the container (or old if updated)
    :param remote_image: remote image for the container (or current if updated)
    :param local_manifest: local image manifest (or old if updated)
    :param remote_manifest: remote image manifest (or current if updated)
    """

    container: ContainerInspectResult
    action: Literal["update", "check", None]
    protected: bool  # Whether container labeled with dev.quenary.tugtainer.protected=true, so it cannot be stopped and updated
    service_name: str | None  # docker compose service name
    compose_deps: list[str]  # docker compose dependencies
    tugtainer_deps: list[str]  # tugtainer dependencies
    temp_result: ContainerCheckResultType | None = None
    image_spec: str | None = None
    config: CreateContainerRequestBodySchema | None = None
    commands: list[list[str]] = field(default_factory=list)
    local_image: ImageInspectResult | None = None
    remote_image: ImageInspectResult | None = None
    local_manifest: ManifestInspectSchema | None = None
    remote_manifest: ManifestInspectSchema | None = None

    @property
    def name(self) -> str:
        """
        This is helper to get name with proper typing.
        Name of the container cannot be None
        """
        return self.container.name or ""


@dataclass
class ContainerGroup:
    """
    Container group for further processing,
    where list is in order of dependency,
    first is most dependable and last is most dependant.
    :param name: name of the group
    :param containers: list of associated containers
    """

    name: str
    containers: list[ContainerGroupItem]


def _get_group_name(c: ContainerInspectResult) -> str:
    """
    Get container's group name.
    If container is a part of compose project, it will be extracted from labels.
    If not, uuid will be used.
    """
    labels = c.config.labels if c.config and c.config.labels else {}
    proj = labels.get("com.docker.compose.project", "")
    fil = labels.get("com.docker.compose.project.config_files", "")
    if proj or fil:
        return f"{proj}:{fil}"
    return str(uuid.uuid4())


def _get_service_name(
    container: ContainerInspectResult,
) -> str | None:
    """Extract service name from compose label."""
    labels = (
        container.config.labels
        if container.config and container.config.labels
        else {}
    )
    return labels.get("com.docker.compose.service", None)


def _get_dependencies(
    container: ContainerInspectResult, label: str
) -> list[str]:
    """Get list of dependencies from label"""
    labels: dict[str, str] = (
        container.config.labels
        if container.config and container.config.labels
        else {}
    )

    # E.g. "service1:condition:value,service2:condition:value"
    depends_on_label: str = labels.get(label, "")

    if not depends_on_label:
        return []

    dependencies: list[str] = []
    for dep in depends_on_label.split(","):
        parts = dep.strip().split(":")  # first part is service name
        if parts:
            name = parts[0].strip()
            if name:
                dependencies.append(name)

    return dependencies


def _sort_containers_by_dependencies(
    containers: list[ContainerGroupItem],
) -> list[ContainerGroupItem]:
    """
    Sort containers so that those on which others depend come first.
    Use the com.docker.compose.depends_on label, if present.
    """

    def _sort(
        c_map: dict[str, ContainerGroupItem],
        d_map: dict[str, list[str]],
    ) -> list[ContainerGroupItem]:
        """
        Sort with maps
        :param c_map: map key (name or service name) to container
        :param d_map: map key (name or service name) to dependencies
        """
        visited: set[str] = set()
        result: list[ContainerGroupItem] = []

        def visit(key: str) -> None:
            if key in visited:
                return
            visited.add(key)
            # Check all dependencies first
            for dep in d_map[key]:
                if dep in c_map:
                    visit(dep)
            # Then add current service
            if key in c_map:
                result.append(c_map[key])

        for k in c_map:
            visit(k)
        return result

    # By custom labels, key is container name
    custom_c_map: dict[str, ContainerGroupItem] = {}
    custom_d_map: dict[str, list[str]] = {}
    for c in containers:
        key = c.name
        custom_c_map[key] = c
        custom_d_map[key] = c.tugtainer_deps
    res1 = _sort(custom_c_map, custom_d_map)

    # By compose labels, key is service name
    compose_c_map: dict[str, ContainerGroupItem] = {}
    compose_d_map: dict[str, list[str]] = {}
    for c in res1:
        key = c.service_name or c.name
        compose_c_map[key] = c
        compose_d_map[key] = c.compose_deps
    res2 = _sort(compose_c_map, compose_d_map)

    return res2


def _get_action(
    db_item: ContainersModel | None,
) -> Literal["update", "check", None]:
    """Get action from db"""
    if db_item and db_item.check_enabled:
        return "update" if db_item.update_enabled else "check"
    return None


def _get_db_item(
    c: ContainerInspectResult, items: list[ContainersModel]
) -> ContainersModel | None:
    return next(
        (item for item in items if item.name == c.name),
        None,
    )


def _get_container_group_item(
    c: ContainerInspectResult, c_db: ContainersModel
) -> ContainerGroupItem:
    return ContainerGroupItem(
        container=c,
        action=_get_action(c_db),
        protected=is_protected_container(c),
        service_name=_get_service_name(c),
        compose_deps=_get_dependencies(
            c, DOCKER_COMPOSE_DEPENDS_ON_LABEL
        ),
        tugtainer_deps=_get_dependencies(
            c, TUGTAINER_DEPENDS_ON_LABEL
        ),
    )


def get_container_group(
    target: ContainerInspectResult,
    containers: list[ContainerInspectResult],
    containers_db: list[ContainersModel],
    update: bool,
) -> ContainerGroup:
    """
    Get container group by single container.
    :param target: target container
    :param containers: list of all host's containers
    :param containers_db: list of  all host's container's db data
    :param update: force update flag (for manual update, ignores selection)
    :returns: group of containers which contains target
    """
    target_c_gn = _get_group_name(target)
    target_db_item = _get_db_item(target, containers_db)
    action = _get_action(target_db_item)
    if update:
        action = "update"
    t_compose_deps = _get_dependencies(
        target, DOCKER_COMPOSE_DEPENDS_ON_LABEL
    )
    t_tugtainer_deps = _get_dependencies(
        target, TUGTAINER_DEPENDS_ON_LABEL
    )
    target_item = ContainerGroupItem(
        container=target,
        action=action,
        protected=is_protected_container(target),
        service_name=_get_service_name(target),
        compose_deps=t_compose_deps,
        tugtainer_deps=t_tugtainer_deps,
    )
    group = ContainerGroup(
        name=target_c_gn,
        containers=[target_item],
    )
    others = [
        item
        for item in containers
        if item != target and item.name != target.name
    ]
    for c in others:
        # For containers from the same compose project the group name will be the same.
        c_gn = _get_group_name(c)
        c_tugtainer_deps = _get_dependencies(
            c, TUGTAINER_DEPENDS_ON_LABEL
        )
        if (
            c_gn == target_c_gn
            or c.name in t_tugtainer_deps
            or target.name in c_tugtainer_deps
        ):
            c_db = _get_db_item(c, containers_db)
            item = _get_container_group_item(c, c_db)
            group.containers.append(item)

    group.containers = _sort_containers_by_dependencies(
        group.containers
    )
    return group


def get_containers_groups(
    containers: list[ContainerInspectResult],
    containers_db: list[ContainersModel],
) -> dict[str, ContainerGroup]:
    """
    Get all container groups for further processing,
    where list of containers is in order of dependency,
    first is most dependable and last is most dependant.
    :param containers: list of all host's containers
    :param containers_db: list of all host's container's db data
    """
    groups: dict[str, ContainerGroup] = {}

    for c in containers:
        db_item = _get_db_item(c, containers_db)
        item = _get_container_group_item(c, db_item)

        # For containers from the same compose project the group name will be the same.
        c_gn = _get_group_name(c)
        group = groups.get(c_gn, None)
        if not group:
            group = ContainerGroup(
                name=c_gn,
                containers=[],
            )
            groups[c_gn] = group
        group.containers.append(item)

    # Add custom dependencies to groups
    for g in groups.values():
        g_tugtainer_deps: set[str] = {
            s for item in g.containers for s in item.tugtainer_deps
        }
        g_conts: set[str] = {item.name for item in g.containers}
        dep_conts = [
            c
            for c in containers
            if c.name not in g_conts and c.name in g_tugtainer_deps
        ]
        for c in dep_conts:
            db_item = _get_db_item(c, containers_db)
            item = _get_container_group_item(c, db_item)
            g.containers.append(item)

    # Filter only unique groups
    group_items: list[tuple[frozenset[str], ContainerGroup]] = []
    for g in groups.values():
        cont_set = frozenset[str](item.name for item in g.containers)
        group_items.append((cont_set, g))
    # Removing same groups
    unique_by_set: dict[frozenset[str], ContainerGroup] = {}
    for cont_set, g in group_items:
        if cont_set not in unique_by_set:
            unique_by_set[cont_set] = g
    # Back to list
    group_items = list(unique_by_set.items())
    # Removing groups whose containers are a subset of another group
    unique_groups: list[ContainerGroup] = []
    for i, (s1, g1) in enumerate(group_items):
        is_subset = False
        for j, (s2, g2) in enumerate(group_items):
            if i != j and s1 < s2:  # Strict subset
                is_subset = True
                break
        if not is_subset:
            unique_groups.append(g1)

    # Sorting
    for g in unique_groups:
        g.containers = _sort_containers_by_dependencies(g.containers)

    return {g.name: g for g in unique_groups}
