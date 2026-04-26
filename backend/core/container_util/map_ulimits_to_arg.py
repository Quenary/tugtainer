from collections.abc import Iterable

from python_on_whales.components.container.models import (
    ContainerUlimit,
)


def map_ulimits_to_arg(
    ulimits: Iterable[ContainerUlimit] | None,
) -> list[str]:
    """Map docker inspect ulimits to run/create arg"""
    res: list[str] = []
    if not ulimits:
        return res

    for lim in ulimits:
        res.append(f"{lim.name}={lim.soft or 0}:{lim.hard or 0}")
    return res
