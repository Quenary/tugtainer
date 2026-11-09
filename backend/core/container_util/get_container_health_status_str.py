from shared.runtime.runtime_models import (
    ContainerInspectResult,
)


def get_container_health_status_str(c: ContainerInspectResult) -> str:
    """
    Get container health status str
    or unknown if health property missing.
    """
    if not c.state or not c.state.health:
        return "unknown"
    return c.state.health.status or "unknown"
