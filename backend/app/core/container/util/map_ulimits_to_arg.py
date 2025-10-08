from python_on_whales.components.container.models import (
    ContainerUlimit,
)
from typing import Iterable


def map_ulimits_to_arg(
    ulimits: Iterable[ContainerUlimit] | None,
) -> list[str]:
    """Map docker inspect ulimits to run/create arg"""
    res: list[str] = []
    if not ulimits:
        return res

    for l in ulimits:
        res.append(f"{l.name}={l.soft or 0}:{l.hard or 0}")
    return res
