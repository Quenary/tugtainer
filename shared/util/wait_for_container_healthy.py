import asyncio
import time
from collections.abc import Awaitable, Callable

from shared.runtime.runtime_models import ContainerInspectResult


def _health_status(container: ContainerInspectResult) -> str:
    state = container.state
    if not state or not state.health:
        return "unknown"
    return state.health.status or "unknown"


def _is_running(container: ContainerInspectResult) -> bool:
    state = container.state
    return bool(state and state.status == "running")


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
    state = container.state
    has_healthcheck = bool(state and state.health)
    container_id = container.id
    if not container_id:
        return False, container
    start = time.time()
    while time.time() - start < timeout:
        container = await inspect(container_id)
        if has_healthcheck:
            if _health_status(container) == "healthy":
                return True, container
        elif _is_running(container):
            return True, container
        await asyncio.sleep(interval)
    container = await inspect(container_id)
    # On last attempt assume unknown is also healthy
    if _is_running(container) and _health_status(container) in [
        "healthy",
        "unknown",
    ]:
        return True, container
    return False, container
