from python_on_whales.components.container.cli_wrapper import (
    Container,
)


def get_container_health_status_str(c: Container) -> str:
    """
    Get container health status str
    or unknown if health property missing.
    """
    if not c.state.health:
        return "unknown"
    return c.state.health.status or "unknown"
