import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any


def _health_status(container: Any) -> str:
    state = getattr(container, "state", None)
    if not state or not getattr(state, "health", None):
        return "unknown"
    return getattr(state.health, "status", None) or "unknown"


def _is_running(container: Any) -> bool:
    state = getattr(container, "state", None)
    return bool(state and getattr(state, "status", None) == "running")


async def wait_for_container_healthy(
    inspect: Callable[[str], Awaitable[Any]],
    container: Any,
    timeout: int = 60,
    interval: float = 5,
) -> tuple[bool, Any]:
    """
    Wait for container healthy status or timeout.
    If the healthcheck property is missing,
    wait only for running state.
    :param inspect: async function returning fresh inspect data by container id
    """
    state = getattr(container, "state", None)
    has_healthcheck = bool(state and getattr(state, "health", None))
    id = getattr(container, "id", None)
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
