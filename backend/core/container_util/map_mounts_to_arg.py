import posixpath
from typing import Any

from shared.runtime.runtime_errors import RuntimePreflightError
from shared.runtime.runtime_models import Mount
from shared.schemas.container_schemas import CreateMount


def map_host_mounts(
    host_mounts: list[Mount] | None,
    binds: list[str] | None,
    runtime_mounts: list[Mount] | None,
) -> tuple[list[str], list[CreateMount]]:
    """Build recreate mounts from HostConfig, using runtime mounts as a fallback.

    ``HostConfig.Mounts`` is copied in long syntax. ``HostConfig.Binds`` strings
    are kept intact, including SELinux and propagation flags. Runtime ``Mounts``
    supply the anonymous volume ``Name`` and any destination HostConfig does
    not already describe.
    """
    runtime_by_dest = {
        dest: mount
        for mount in runtime_mounts or []
        if (dest := _destination(mount)) is not None
    }
    covered: set[str] = set()
    mounts: list[CreateMount] = []
    for host_mount in host_mounts or []:
        dest = _destination(host_mount)
        if dest is None:
            raise RuntimePreflightError("HostConfig.Mounts entry is missing a target")
        if dest in covered:
            continue
        covered.add(dest)
        mounts.append(_create_mount(host_mount, runtime_by_dest.get(dest)))

    kept_binds: list[str] = []
    for bind in binds or []:
        dest = _bind_destination(bind)
        if dest is None:
            raise RuntimePreflightError(f"Cannot represent bind {bind!r}")
        if dest in covered:
            _reject_unrepresented_selinux(bind, dest)
            continue
        covered.add(dest)
        kept_binds.append(bind)

    for dest, runtime in runtime_by_dest.items():
        if dest in covered:
            continue
        covered.add(dest)
        _reject_runtime_selinux(runtime, dest)
        mounts.append(_create_mount(runtime, None))

    return kept_binds, mounts


def _create_mount(mount: Mount, runtime: Mount | None) -> CreateMount:
    dest = _destination(mount)
    if dest is None:
        raise RuntimePreflightError("Mount is missing a target")
    source = _source(mount)
    if not source and runtime is not None:
        source = _source(runtime)
    bind_options = _bind_options(mount)
    volume_options = _volume_options(mount)
    return CreateMount(
        type=mount.type or "volume",
        target=mount.target or mount.destination or dest,
        source=source,
        read_only=_read_only(mount),
        consistency=mount.consistency,
        bind_options=bind_options,
        volume_options=volume_options,
        tmpfs_options=mount.tmpfs_options,
        image_options=mount.image_options,
    )


def _destination(mount: Mount) -> str | None:
    raw = mount.target or mount.destination
    if not raw:
        return None
    return posixpath.normpath(raw)


def _source(mount: Mount) -> str | None:
    if (mount.type or "volume") == "volume" and mount.name:
        return mount.name
    return mount.source


def _read_only(mount: Mount) -> bool | None:
    if mount.read_only:
        return True
    if mount.rw is False:
        return True
    return None


def _bind_options(mount: Mount) -> dict[str, Any] | None:
    options = dict(mount.bind_options or {})
    propagation = mount.propagation
    if propagation and not _has_key(options, "Propagation"):
        options["Propagation"] = propagation
    return options or None


def _volume_options(mount: Mount) -> dict[str, Any] | None:
    options = dict(mount.volume_options or {})
    driver = mount.driver
    if driver and driver != "local" and not _has_key(options, "DriverConfig"):
        options["DriverConfig"] = {"Name": driver}
    return options or None


def _has_key(options: dict[str, Any], canonical: str) -> bool:
    return any(str(key).lower() == canonical.lower() for key in options)


def _bind_destination(bind: str) -> str | None:
    parts = bind.split(":")
    if len(parts) < 2 or not parts[1].startswith("/"):
        return None
    return posixpath.normpath(parts[1])


def _reject_unrepresented_selinux(bind: str, dest: str) -> None:
    parts = bind.split(":")
    if len(parts) < 3:
        return
    flags = {flag for flag in parts[2].split(",") if flag}
    if flags & {"z", "Z"}:
        raise RuntimePreflightError(
            f"Bind for {dest} has SELinux flags that the HostConfig.Mounts "
            "entry for the same target cannot represent"
        )


def _reject_runtime_selinux(mount: Mount, dest: str) -> None:
    flags = {flag for flag in (mount.mode or "").split(",") if flag}
    if flags & {"z", "Z"}:
        raise RuntimePreflightError(
            f"Mount {dest} has SELinux mode {mount.mode!r} and no HostConfig.Binds "
            "entry to preserve it"
        )
