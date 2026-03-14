import logging
from typing import cast
from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from sqlalchemy import select
from backend.core.agent_client import AgentClient
from backend.core.container_group.container_group_schemas import (
    ContainerGroupItem,
)
from backend.modules.containers.containers_model import (
    ContainersModel,
)
from backend.core.action_result import (
    GroupActionResult,
)
from backend.util.now import now
from backend.db.session import async_session_maker
from shared.schemas.network_schemas import NetworkDisconnectBodySchema


async def update_containers_data_after_action(
    result: GroupActionResult | None,
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
