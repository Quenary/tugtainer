from python_on_whales.components.container.cli_wrapper import (
    Container,
)


def get_container_image_spec(c: Container) -> str | None:
    return c.config.image
