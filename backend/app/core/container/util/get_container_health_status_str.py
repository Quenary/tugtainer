from python_on_whales.components.container.cli_wrapper import (
    Container,
)


def get_container_health_status_str(c: Container) -> str:
    if c.state.status and c.state.health:
        return c.state.health.status or "unknown"
    return "unknown"
