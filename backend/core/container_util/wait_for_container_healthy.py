from backend.core.agent_client import AgentClient
from shared.runtime.runtime_models import (
    ContainerInspectResult,
)
from shared.util.wait_for_container_healthy import (
    wait_for_container_healthy as _wait_for_container_healthy,
)


async def wait_for_container_healthy(
    client: AgentClient,
    container: ContainerInspectResult,
    timeout: int = 60,
) -> tuple[bool, ContainerInspectResult]:
    """
    Wait for container healthy status or timeout.
    If the healthcheck property is missing,
    wait only for running state.
    """
    return await _wait_for_container_healthy(
        client.container.inspect, container, timeout
    )
