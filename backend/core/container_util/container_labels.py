from collections.abc import Sequence

from python_on_whales.components.container.models import (
    ContainerInspectResult,
)

from backend.const import (
    TUGTAINER_AUTO_CHECK_LABEL,
    TUGTAINER_AUTO_UPDATE_LABEL,
    TUGTAINER_HIDDEN_LABEL,
    TUGTAINER_PROTECTED_LABEL,
)


def parse_bool_label(val: str | None) -> bool | None:
    """Parse boolean value from label string."""
    if not isinstance(val, str):
        return None
    cleaned = val.strip().lower()
    if cleaned in ("true", "1", "yes", "on"):
        return True
    if cleaned in ("false", "0", "no", "off"):
        return False
    return None


def _container_labels(
    container: ContainerInspectResult | None,
) -> dict[str, str] | None:
    if container is None:
        return None
    config = getattr(container, "config", None)
    labels = getattr(config, "labels", None) if config else None
    if not labels:
        return None
    return labels


def _bool_label(
    container: ContainerInspectResult | None,
    key: str,
) -> bool | None:
    labels = _container_labels(container)
    if not labels:
        return None
    return parse_bool_label(labels.get(key))


def get_container_auto_check_label(
    container: ContainerInspectResult | None,
) -> bool | None:
    """Get boolean value of dev.quenary.tugtainer.auto_check label, or None if not set."""
    return _bool_label(container, TUGTAINER_AUTO_CHECK_LABEL)


def get_container_auto_update_label(
    container: ContainerInspectResult | None,
) -> bool | None:
    """Get boolean value of dev.quenary.tugtainer.auto_update label, or None if not set."""
    return _bool_label(container, TUGTAINER_AUTO_UPDATE_LABEL)


def get_container_protected_label(
    container: ContainerInspectResult | None,
) -> bool | None:
    """Get boolean value of dev.quenary.tugtainer.protected label, or None if not set."""
    return _bool_label(container, TUGTAINER_PROTECTED_LABEL)


def get_container_hidden_label(
    container: ContainerInspectResult | None,
) -> bool | None:
    """Get boolean value of dev.quenary.tugtainer.hidden label, or None if not set."""
    return _bool_label(container, TUGTAINER_HIDDEN_LABEL)


def exclude_hidden_containers(
    containers: Sequence[ContainerInspectResult],
) -> list[ContainerInspectResult]:
    """Drop containers labeled as hidden from the application scope."""
    return [c for c in containers if get_container_hidden_label(c) is not True]
