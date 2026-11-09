def systemd_managed_reason(labels: dict[str, str] | None) -> str | None:
    """
    Why a container must not be recreated, or None when recreation is allowed.

    Quadlet and other systemd-managed containers are replaced by the unit,
    so stop/remove would fight the service manager.
    """
    if not labels:
        return None
    if "PODMAN_SYSTEMD_UNIT" in labels:
        unit = labels.get("PODMAN_SYSTEMD_UNIT") or ""
        shown = f"={unit}" if unit else ""
        return (
            f"has label PODMAN_SYSTEMD_UNIT{shown}. "
            "Quadlet-managed containers cannot be recreated through the engine API. "
            "Use `podman auto-update` instead."
        )
    if labels.get("manager") == "systemd" or any(
        "quadlet" in key.lower() for key in labels
    ):
        return (
            "is managed by systemd or Quadlet "
            "(label manager=systemd or a label containing quadlet). "
            "It cannot be recreated through the engine API. "
            "Use `podman auto-update` instead."
        )
    return None
