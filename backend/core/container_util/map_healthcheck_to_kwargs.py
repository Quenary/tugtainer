from typing import Any

from python_on_whales.components.container.models import (
    ContainerHealthCheck,
)


def _ns_to_sec(ns: int | None) -> int | None:
    return int(ns / 1_000_000_000) if ns else None


def _test_list(cfg: ContainerHealthCheck | None) -> list[str]:
    if not cfg or not cfg.test:
        return []
    return list(cfg.test)


def _health_cmd(test: list[str]) -> str | None:
    if len(test) <= 1:
        return None
    if test[0] in ("CMD", "CMD-SHELL"):
        return " ".join(test[1:])
    return " ".join(test)


def map_healthcheck_to_kwargs(
    cfg: ContainerHealthCheck | None,
    image_cfg: ContainerHealthCheck | None = None,
    *,
    inherit_matching: bool = False,
) -> dict[str, Any]:
    """Map docker inspect healthcheck to run/create kwargs.

    Docker CLI always stores --health-cmd as CMD-SHELL, so an image-defined
    exec-form (CMD) healthcheck must be inherited rather than re-specified.
    When inherit_matching is set, fields that already match the image are omitted.
    """
    if not cfg:
        if inherit_matching and not image_cfg:
            return {}
        return {"healthcheck": False}

    test = _test_list(cfg)
    result: dict[str, Any] = {
        "healthcheck": True,
        "health_cmd": _health_cmd(test),
        "health_interval": _ns_to_sec(cfg.interval),
        "health_timeout": _ns_to_sec(cfg.timeout),
        "health_retries": cfg.retries,
        "health_start_period": _ns_to_sec(cfg.start_period),
    }

    if not inherit_matching or test != _test_list(image_cfg):
        return result

    # Same test as the image: drop --health-cmd so Docker keeps CMD / CMD-SHELL.
    result.pop("health_cmd", None)
    result.pop("healthcheck", None)

    image_interval = _ns_to_sec(image_cfg.interval) if image_cfg else None
    image_timeout = _ns_to_sec(image_cfg.timeout) if image_cfg else None
    image_retries = image_cfg.retries if image_cfg else None
    image_start_period = _ns_to_sec(image_cfg.start_period) if image_cfg else None

    if result["health_interval"] == image_interval:
        result.pop("health_interval", None)
    if result["health_timeout"] == image_timeout:
        result.pop("health_timeout", None)
    if result["health_retries"] == image_retries:
        result.pop("health_retries", None)
    if result["health_start_period"] == image_start_period:
        result.pop("health_start_period", None)

    return result
