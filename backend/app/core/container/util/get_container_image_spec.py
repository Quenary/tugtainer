from python_on_whales.components.container.cli_wrapper import (
    Container,
)


def get_container_image_spec(c: Container) -> str | None:
    """Get container image spec e.g. quenary/tugtainer:latest"""
    return c.config.image
