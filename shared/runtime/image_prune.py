"""Image prune filters and a text result the notification template can print."""

from typing import Any

_UNITS: tuple[str, ...] = ("B", "kB", "MB", "GB", "TB", "PB")


def prune_filters(
    prune_all: bool | None,
    filters: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Build the Engine API prune filter.

    ``prune_all`` asks the daemon to delete every unused image, which is the
    ``dangling=false`` filter. Without it the daemon keeps its default and
    removes dangling images only, so an empty filter set is omitted.
    """
    merged = dict(filters or {})
    if prune_all:
        merged["dangling"] = ["false"]
    return merged or None


def format_image_prune_result(payload: dict[str, Any]) -> str:
    deleted = payload.get("ImagesDeleted") or []
    if not isinstance(deleted, list):
        deleted = []
    untagged = sum(
        1 for item in deleted if isinstance(item, dict) and item.get("Untagged")
    )
    removed = sum(
        1 for item in deleted if isinstance(item, dict) and item.get("Deleted")
    )
    reclaimed = payload.get("SpaceReclaimed") or 0
    if isinstance(reclaimed, bool) or not isinstance(reclaimed, int):
        reclaimed = 0
    lines = [
        f"Deleted Images: {removed}",
        f"Untagged Images: {untagged}",
        f"Total reclaimed space: {_human_bytes(reclaimed)}",
    ]
    return "\n".join(lines)


def _human_bytes(size: int) -> str:
    value = float(size)
    unit = _UNITS[-1]
    for unit in _UNITS:
        if value < 1024 or unit == _UNITS[-1]:
            break
        value /= 1024
    if unit == "B":
        return f"{int(value)}B"
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return f"{text}{unit}"
