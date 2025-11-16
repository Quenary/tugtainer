from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from backend.const import TUGTAINER_PROTECTED_LABEL


def is_protected_container(container: ContainerInspectResult) -> bool:
    """Whether container labeled with dev.quenary.tugtainer.protected=true"""
    return bool(
        container.config
        and container.config.labels
        and container.config.labels.get(
            TUGTAINER_PROTECTED_LABEL, "false"
        ).lower()
        == "true"
    )
