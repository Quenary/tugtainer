from python_on_whales.components.container.models import (
    ContainerInspectResult,
)


def get_service_name(
    container: ContainerInspectResult,
) -> str | None:
    """Extract service name from compose label."""
    labels = (
        container.config.labels
        if container.config and container.config.labels
        else {}
    )
    return labels.get("com.docker.compose.service", None)
