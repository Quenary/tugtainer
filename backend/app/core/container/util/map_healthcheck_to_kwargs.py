from datetime import timedelta
from typing import Any, Dict, Optional
from python_on_whales.components.container.models import (
    ContainerHealthCheck,
)


def map_healthcheck_to_kwargs(
    cfg: ContainerHealthCheck | None,
) -> Dict[str, Any]:
    """Map docker inspect healthcheck to run/create kwargs"""
    if not cfg:
        return {"healthcheck": False}

    def ns_to_td(ns: Optional[int]) -> Optional[timedelta]:
        return timedelta(seconds=ns / 1_000_000_000) if ns else None

    test = cfg.test
    health_cmd = None
    if isinstance(test, list) and len(test) > 1:
        if test[0] in ("CMD", "CMD-SHELL"):
            health_cmd = " ".join(test[1:])
        else:
            health_cmd = " ".join(test)

    return {
        "healthcheck": True,
        "health_cmd": health_cmd,
        "health_interval": ns_to_td(cfg.interval),
        "health_timeout": ns_to_td(cfg.timeout),
        "health_retries": cfg.retries,
        "health_start_period": ns_to_td(cfg.start_period),
    }
