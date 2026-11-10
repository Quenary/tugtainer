from collections.abc import Iterable
from typing import Any

from shared.runtime.runtime_models import (
    ContainerLogConfig,
)


def map_log_config_to_kwargs(
    cfg: ContainerLogConfig | None,
) -> dict[str, Any]:
    """Map docker inspect log config to run/create kwargs"""
    if not cfg:
        return {
            "log_driver": None,
            "log_options": (),
        }

    config: dict = cfg.config or {}
    log_options: Iterable[str] = tuple(f"{k}={v}" for k, v in config.items())
    return {
        "log_driver": cfg.type,
        "log_options": log_options,
    }
