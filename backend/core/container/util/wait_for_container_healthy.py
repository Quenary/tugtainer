import time
from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from backend.core.agent_client import AgentClient
from .get_container_health_status_str import (
    get_container_health_status_str,
)
import asyncio
from .is_running_container import is_running_container


async def wait_for_container_healthy(
    client: AgentClient,
    container: ContainerInspectResult,
    timeout: int = 60,
) -> bool:
    """
    Wait for container healthy status or timeout.
    If the healthcheck property is missing,
    wait only for running state.
    """
    has_healthcheck = bool(container.state and container.state.health)
    id = container.id
    if not id:
        return False
    start = time.time()
    while time.time() - start < timeout:
        container = await client.container.inspect(id)
        if has_healthcheck:
            health = get_container_health_status_str(container)
            if health == "healthy":
                return True
        elif is_running_container(container):
            return True
        await asyncio.sleep(5)
    container = await client.container.inspect(id)
    health = get_container_health_status_str(container)
    # On last attempt assume unknown is also healthy
    if is_running_container(container) and health in [
        "healthy",
        "unknown",
    ]:
        return True
    return False
