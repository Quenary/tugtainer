from python_on_whales.components.container.models import (
    ContainerInspectResult,
)

from backend.const import (
    TUGTAINER_AUTO_CHECK_LABEL,
    TUGTAINER_AUTO_UPDATE_LABEL,
)


def parse_bool_label(val: str | None) -> bool | None:
    """Parse boolean value from label string."""
    if val is None:
        return None
    cleaned = val.strip().lower()
    if cleaned in ("true", "1", "yes", "on"):
        return True
    if cleaned in ("false", "0", "no", "off"):
        return False
    return None


def get_container_auto_check_label(
    container: ContainerInspectResult | None,
) -> bool | None:
    """Get boolean value of dev.quenary.tugtainer.auto_check label, or None if not set."""
    if container is None:
        return None
    config = getattr(container, "config", None)
    labels = getattr(config, "labels", None) if config else None
    if not labels:
        return None
    return parse_bool_label(labels.get(TUGTAINER_AUTO_CHECK_LABEL))


def get_container_auto_update_label(
    container: ContainerInspectResult | None,
) -> bool | None:
    """Get boolean value of dev.quenary.tugtainer.auto_update label, or None if not set."""
    if container is None:
        return None
    config = getattr(container, "config", None)
    labels = getattr(config, "labels", None) if config else None
    if not labels:
        return None
    return parse_bool_label(labels.get(TUGTAINER_AUTO_UPDATE_LABEL))
