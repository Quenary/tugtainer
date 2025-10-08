from typing import List
from python_on_whales.components.container.models import (
    ContainerDevice,
)


def map_devices_to_list(
    devices: List[ContainerDevice] | None,
) -> list[str]:
    """
    Map docker inspect devices to list of strings
    """
    res: list[str] = []
    if not devices:
        return res

    for dev in devices:
        if not dev.path_on_host or not dev.path_in_container:
            continue

        permissions = dev.cgroup_permissions or "rwm"
        res.append(
            f"{dev.path_on_host}:{dev.path_in_container}:{permissions}"
        )

    return res
