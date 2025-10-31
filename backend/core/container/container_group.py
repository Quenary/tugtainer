from dataclasses import dataclass, field
from typing import Literal
from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from python_on_whales.components.image.models import (
    ImageInspectResult,
)
from backend.helpers.self_container import is_self_container
from backend.db.models import ContainersModel
import uuid

from shared.schemas.container_schemas import (
    CreateContainerRequestBodySchema,
)


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
    :param old_image: current image of the container
    :param new_image: possible new image for the container
    """

    container: ContainerInspectResult
    action: Literal["update", "check", None]
    available: bool = False
    image_spec: str | None = None
    config: CreateContainerRequestBodySchema | None = None
    commands: list[list[str]] = field(default_factory=list)
    old_image: ImageInspectResult | None = None
    new_image: ImageInspectResult | None = None

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
    :param is_self: is group with self container
    :param containers: list of associated containers
    """

    name: str
    is_self: bool
    containers: list[ContainerGroupItem]


def _get_group_name(c: ContainerInspectResult) -> str:
    """
    Get container's group name.
    If container is a part of compose project, it will be extracted from labels.
    If not, container name is used.
    """
    labels = c.config.labels if c.config and c.config.labels else {}
    proj = labels.get("com.docker.compose.project", "")
    fil = labels.get("com.docker.compose.project.config_files", "")
    if proj or fil:
        return f"{proj}:{fil}"
    return c.name if c.name else str(uuid.uuid4())


def _get_service_name(container: ContainerInspectResult) -> str:
    """Extract service name from labels"""
    labels = (
        container.config.labels
        if container.config and container.config.labels
        else {}
    )
    return labels.get(
        "com.docker.compose.service", container.name or ""
    )


def _get_dependencies(container: ContainerInspectResult) -> list[str]:
    """Get list of dependencies from labels"""
    labels: dict[str, str] = (
        container.config.labels
        if container.config and container.config.labels
        else {}
    )

    # E.g. "service1:condition:value,service2:condition:value"
    depends_on_label: str = labels.get(
        "com.docker.compose.depends_on", ""
    )

    if not depends_on_label:
        return []

    dependencies: list[str] = []
    for dep in depends_on_label.split(","):
        parts = dep.split(":")  # first part is service name
        if parts:
            dependencies.append(parts[0])

    return dependencies


def _sort_containers_by_dependencies(
    containers: list[ContainerGroupItem],
) -> list[ContainerGroupItem]:
    """
    Sort containers so that those on which others depend come first.
    Use the com.docker.compose.depends_on label, if present.
    """
    cont_map: dict[str, ContainerGroupItem] = (
        {}
    )  # map service name to container
    deps_map: dict[str, list[str]] = (
        {}
    )  # map service name to dependencies

    for c in containers:
        cont = c.container
        service_name = _get_service_name(cont)
        cont_map[service_name] = c
        deps_map[service_name] = _get_dependencies(cont)

    visited: set[str] = set()
    result: list[ContainerGroupItem] = []

    def visit(service: str) -> None:
        if service in visited:
            return
        visited.add(service)

        # Check all dependencies first
        for dep in deps_map[service]:
            if dep in cont_map:
                visit(dep)

        # Then add current service
        if service in cont_map:
            result.append(cont_map[service])

    for service in cont_map:
        visit(service)

    return result


def _get_action(
    db_item: ContainersModel | None,
) -> Literal["update", "check", None]:
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
    if is_self_container(target):
        target_item = ContainerGroupItem(
            container=target, action="check"
        )
        return ContainerGroup(
            name="self_container",
            containers=[target_item],
            is_self=True,
        )
    target_c_gn = _get_group_name(target)
    target_db_item = _get_db_item(target, containers_db)
    action = _get_action(target_db_item)
    if update:
        action = "update"
    target_item = ContainerGroupItem(container=target, action=action)
    group = ContainerGroup(
        name=target_c_gn,
        containers=[target_item],
        is_self=False,
    )
    others = [
        item
        for item in containers
        if not is_self_container(item) and item != target
    ]
    for c in others:
        c_gn = _get_group_name(c)
        if c_gn == target_c_gn:
            c_db = _get_db_item(c, containers_db)
            item = ContainerGroupItem(
                container=c, action=_get_action(c_db)
            )
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
    where list is in order of dependency,
    first is most dependable and last is most dependant.
    :param containers: list of all host's containers
    :param containers_db: list of  all host's container's db data
    """
    groups: dict[str, ContainerGroup] = {}

    for c in containers:
        if is_self_container(c):
            item = ContainerGroupItem(container=c, action="check")
            groups["self_container"] = ContainerGroup(
                name="self_container", containers=[item], is_self=True
            )
            continue

        db_item = _get_db_item(c, containers_db)
        action = _get_action(db_item)
        item = ContainerGroupItem(container=c, action=action)

        c_gn = _get_group_name(c)
        group = groups.get(c_gn, None)
        if not group:
            group = ContainerGroup(
                name=c_gn, containers=[], is_self=False
            )
            groups[c_gn] = group
        group.containers.append(item)

    for g in groups.values():
        g.containers = _sort_containers_by_dependencies(g.containers)
    return groups
