import asyncio
import time
from collections.abc import Awaitable, Callable

from python_on_whales.components.container.models import (
    ContainerInspectResult,
)


def _health_status(container: ContainerInspectResult) -> str:
    if not container.state or not container.state.health:
        return "unknown"
    return container.state.health.status or "unknown"


def _is_running(container: ContainerInspectResult) -> bool:
    return bool(container.state and container.state.status == "running")


async def wait_for_container_healthy(
    inspect: Callable[[str], Awaitable[ContainerInspectResult]],
    container: ContainerInspectResult,
    timeout: int = 60,
    interval: float = 5,
) -> tuple[bool, ContainerInspectResult]:
    """
    Wait for container healthy status or timeout.
    If the healthcheck property is missing,
    wait only for running state.
    :param inspect: async function returning fresh inspect data by container id
    """
    has_healthcheck = bool(container.state and container.state.health)
    id = container.id
    if not id:
        return False, container
    start = time.time()
    while time.time() - start < timeout:
        container = await inspect(id)
        if has_healthcheck:
            if _health_status(container) == "healthy":
                return True, container
        elif _is_running(container):
            return True, container
        await asyncio.sleep(interval)
    container = await inspect(id)
    # On last attempt assume unknown is also healthy
    if _is_running(container) and _health_status(container) in [
        "healthy",
        "unknown",
    ]:
        return True, container
    return False, container
