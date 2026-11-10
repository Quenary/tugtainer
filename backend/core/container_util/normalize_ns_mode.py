def normalize_ns_mode(mode: str | None) -> str | None:
    """
    Namespace mode for the engine create body.

    Podman inspect returns ``private`` for the default UTS and user namespace.
    The engine treats an omitted mode as private, and ``private`` is not a
    valid HostConfig value on Docker.
    """
    if not mode or mode == "private":
        return None
    return mode
