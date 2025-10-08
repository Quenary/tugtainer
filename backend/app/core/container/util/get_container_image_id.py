from python_on_whales.components.container.cli_wrapper import (
    Container,
)
import re


def get_container_image_id(c: Container) -> str | None:
    """
    Get container image id without prefix or none
    :returns: <64-hex> | None
    """
    if not c or not c.image:
        return None
    match = re.fullmatch(r"sha256:([0-9a-f]{64})", c.image)
    return match.group(1) if match else None
