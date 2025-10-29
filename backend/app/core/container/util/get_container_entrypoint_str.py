def get_container_entrypoint_str(
    entrypoint: list[str] | str | None,
) -> str | None:
    if not entrypoint:
        return None
    if isinstance(entrypoint, list):
        return " ".join(entrypoint)
    return entrypoint
