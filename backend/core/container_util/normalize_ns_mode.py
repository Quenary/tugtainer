def normalize_ns_mode(mode: str | None) -> str | None:
    """
    Normalize namespace mode for docker CLI create/run.

    Docker CLI accepts '' (default/private) or 'host' for --uts/--userns.
    Podman inspect often returns the literal 'private' for the default mode,
    which Docker CLI rejects as invalid.
    """
    if not mode or mode == "private":
        return None
    return mode
