import logging

from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from sqlalchemy import select

from backend.core.action_result import (
    UpdatePlanResult,
)
from backend.core.agent_client import AgentClient
from backend.db.session import async_session_maker
from backend.modules.containers.containers_model import (
    ContainersModel,
)
from backend.util.now import now
from shared.schemas.network_schemas import NetworkDisconnectBodySchema


async def update_containers_data_after_execution(
    result: UpdatePlanResult | None,
) -> None:
    """Update containers in db after update process"""
    if not result:
        return
    valid_items = [item for item in result.items if item.result]
    if not valid_items:
        return
    _now = now()

    async with async_session_maker() as session:
        container_names = [
            item.container.name for item in valid_items
        ]
        containers = await session.scalars(
            select(ContainersModel).where(
                ContainersModel.host_id == result.host_id,
                ContainersModel.name.in_(container_names),
            )
        )

        containers_map = {c.name: c for c in containers}

        for item in valid_items:
            if container := containers_map.get(
                str(item.container.name), None
            ):
                if item.result == "updated":
                    container.update_available = False
                    container.updated_at = _now
                    container.local_digests = item.remote_digests

        await session.commit()


async def disconnect_all_networks(
    client: AgentClient,
    container: ContainerInspectResult,
    force: bool,
):
    """
    Explicitly disconnects a container from all its networks.
    Prevents 'endpoint already exists' errors during recreation.
    https://github.com/Quenary/tugtainer/issues/119
    """
    if (
        not container.name
        or not container.network_settings
        or not container.network_settings.networks
    ):
        return
    for network in container.network_settings.networks.keys():
        try:
            logging.info(
                f"Disconnecting {container.name} from network {network}"
            )
            await client.network.disconnect(
                NetworkDisconnectBodySchema(
                    network=network,
                    container=container.name,
                    force=force,
                )
            )
        except Exception:
            pass


def get_dependencies(
    container: ContainerInspectResult, label: str
) -> set[str]:
    """Get list of dependencies from label"""
    labels: dict[str, str] = (
        container.config.labels
        if container.config and container.config.labels
        else {}
    )

    # E.g. "service1:condition:value,service2:condition:value"
    # Or "containername1, containername2" for custom label
    depends_on_label: str = labels.get(label, "")

    dependencies: set[str] = set()

    if not depends_on_label:
        return dependencies

    for dep in depends_on_label.split(","):
        parts = dep.strip().split(":")  # first part is service name
        if parts:
            name = parts[0].strip()
            if name:
                dependencies.add(name)

    return dependencies


def get_compose_id(c: ContainerInspectResult) -> str | None:
    """
    Combine labels to get unique id for a compose project
    """
    labels = c.config.labels if c.config and c.config.labels else {}
    proj = labels.get("com.docker.compose.project", "")
    fil = labels.get("com.docker.compose.project.config_files", "")
    if proj or fil:
        return f"{proj}:{fil}"
    return None
