import posixpath

from python_on_whales.components.container.models import Mount

VolumeTuple = tuple[str, str] | tuple[str, str, str]


def map_binds_to_volumes(
    binds: list[str] | None,
    mounts: list[Mount] | None,
) -> tuple[list[VolumeTuple], list[Mount]]:
    """
    Map docker inspect HostConfig.Binds (created with -v / --volume)
    to run/create volumes arg, so the recreated container keeps them
    in HostConfig.Binds. Some tools read volumes only from there (e.g. Unraid).
    A bind is used only if it matches an inspect mount,
    anything else stays a --mount.
    :returns 0: volumes arg
    :returns 1: mounts not covered by the volumes
    """
    mounts = mounts or []
    destinations = {posixpath.normpath(m.destination) for m in mounts if m.destination}
    volumes: list[VolumeTuple] = []
    for bind in binds or []:
        volume = _parse_bind(bind)
        if volume and posixpath.normpath(volume[1]) in destinations:
            volumes.append(volume)

    covered = {posixpath.normpath(v[1]) for v in volumes}
    rest = [
        m
        for m in mounts
        if not m.destination or posixpath.normpath(m.destination) not in covered
    ]
    return volumes, rest


def _parse_bind(bind: str) -> VolumeTuple | None:
    """
    Parse "src:dst" or "src:dst:options" with an absolute dst.
    Anything else (e.g. a Windows path with a drive letter) is skipped.
    """
    parts = bind.split(":")
    if len(parts) not in (2, 3) or not parts[1].startswith("/"):
        return None
    if len(parts) == 2:
        return (parts[0], parts[1])
    return (parts[0], parts[1], parts[2])
