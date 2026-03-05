from typing import Any, Dict, Iterable, Optional
from python_on_whales.components.container.models import (
    ContainerLogConfig,
)


def map_log_config_to_kwargs(
    cfg: ContainerLogConfig | None,
) -> Dict[str, Any]:
    """Map docker inspect log config to run/create kwargs"""
    if not cfg:
        return {
            "log_driver": None,
            "log_options": (),
        }

    config: dict = cfg.config or {}
    log_options: Iterable[str] = tuple(
        f"{k}={v}" for k, v in config.items()
    )
    return {
        "log_driver": cfg.type,
        "log_options": log_options,
    }
