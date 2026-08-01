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
        name = lim.name or ""
        # Podman inspect reports names like "RLIMIT_NOFILE",
        # but the --ulimit flag only accepts the short form ("nofile")
        if name.upper().startswith("RLIMIT_"):
            name = name[len("RLIMIT_") :].lower()
        res.append(f"{name}={lim.soft or 0}:{lim.hard or 0}")
    return res
