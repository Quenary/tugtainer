from python_on_whales.components.container.models import (
    ContainerInspectResult,
)


def get_container_image_spec(c: ContainerInspectResult) -> str | None:
    """Get container image spec e.g. quenary/tugtainer:latest"""
    return c.config.image if c.config else None
