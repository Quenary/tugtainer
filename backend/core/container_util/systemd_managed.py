_SYSTEMD_UNIT = "PODMAN_SYSTEMD_UNIT"


def systemd_managed_reason(
    labels: dict[str, str] | None,
    env: list[str] | None = None,
) -> str | None:
    """
    Why a container must not be recreated, or None when recreation is allowed.

    Podman copies the PODMAN_SYSTEMD_UNIT environment variable into a container
    label of the same name at creation time (podman-auto-update(1)). Quadlet and
    ``podman generate systemd`` set that variable on the unit. Stop/remove would
    fight the service manager.
    """
    unit = _podman_systemd_unit(labels, env)
    if unit is None:
        return None
    shown = f"={unit}" if unit else ""
    return (
        f"has {_SYSTEMD_UNIT}{shown}. "
        "systemd-managed containers cannot be recreated through the engine API. "
        "Use `podman auto-update` instead."
    )


def _podman_systemd_unit(
    labels: dict[str, str] | None,
    env: list[str] | None,
) -> str | None:
    if labels and _SYSTEMD_UNIT in labels:
        return labels.get(_SYSTEMD_UNIT) or ""
    if not env:
        return None
    prefix = f"{_SYSTEMD_UNIT}="
    for item in env:
        if item.startswith(prefix):
            return item.removeprefix(prefix)
    return None
