import re
from python_on_whales.components.container.models import (
    ContainerInspectResult,
)


def get_container_image_id(c: ContainerInspectResult) -> str | None:
    """
    Get container image id without prefix or none
    :returns: <64-hex> | None
    """
    if not c.image:
        return None
    match = re.fullmatch(r"sha256:([0-9a-f]{64})", c.image)
    return match.group(1) if match else None
