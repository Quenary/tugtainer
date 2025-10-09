import time
from python_on_whales.components.container.cli_wrapper import (
    Container,
)
from .get_container_health_status_str import (
    get_container_health_status_str,
)
import asyncio


async def wait_for_container_healthy(
    container: Container, timeout: int = 60
) -> bool:
    """
    Wait for container healthy status or timeout.
    If the healthcheck property is missing,
    wait only for running state.
    """
    has_healthcheck = bool(container.state.health)

    start = time.time()
    while time.time() - start < timeout:
        container.reload()
        if has_healthcheck:
            health = get_container_health_status_str(container)
            if health == "healthy":
                return True
        elif container.state.status == "running":
            return True
        await asyncio.sleep(5)
    container.reload()
    health = get_container_health_status_str(container)
    status = container.state.status
    # On last attempt assume unknown is also healthy
    if status == "running" and health in ["healthy", "unknown"]:
        return True
    return False
