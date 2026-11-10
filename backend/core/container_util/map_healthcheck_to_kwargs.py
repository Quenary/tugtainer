from typing import Any

from shared.runtime.runtime_models import (
    ContainerHealthCheck,
)


def _test_list(cfg: ContainerHealthCheck | None) -> list[str]:
    if not cfg or not cfg.test:
        return []
    return list(cfg.test)


def _same_healthcheck(
    cfg: ContainerHealthCheck,
    image_cfg: ContainerHealthCheck | None,
) -> bool:
    if image_cfg is None:
        return False
    return (
        _test_list(cfg) == _test_list(image_cfg)
        and cfg.interval == image_cfg.interval
        and cfg.timeout == image_cfg.timeout
        and cfg.retries == image_cfg.retries
        and cfg.start_period == image_cfg.start_period
        and cfg.start_interval == image_cfg.start_interval
    )


def _put_durations(
    result: dict[str, Any],
    cfg: ContainerHealthCheck,
    image_cfg: ContainerHealthCheck | None,
    *,
    inherit_matching: bool,
) -> None:
    pairs = (
        ("health_interval", cfg.interval, image_cfg.interval if image_cfg else None),
        ("health_timeout", cfg.timeout, image_cfg.timeout if image_cfg else None),
        ("health_retries", cfg.retries, image_cfg.retries if image_cfg else None),
        (
            "health_start_period",
            cfg.start_period,
            image_cfg.start_period if image_cfg else None,
        ),
        (
            "health_start_interval",
            cfg.start_interval,
            image_cfg.start_interval if image_cfg else None,
        ),
    )
    for key, value, image_value in pairs:
        if value is None:
            continue
        if inherit_matching and value == image_value:
            continue
        result[key] = value


def map_healthcheck_to_kwargs(
    cfg: ContainerHealthCheck | None,
    image_cfg: ContainerHealthCheck | None = None,
    *,
    inherit_matching: bool = False,
) -> dict[str, Any]:
    """Map an inspect healthcheck onto create kwargs.

    ``Test`` is copied verbatim, including ``CMD`` and ``NONE``. Durations stay
    in nanoseconds. When ``inherit_matching`` is set, a healthcheck identical
    to the image is omitted so the new image definition applies. Any other
    container healthcheck is sent with its original ``Test`` list.
    """
    if not cfg:
        if inherit_matching and not image_cfg:
            return {}
        return {"healthcheck": False}

    if inherit_matching and _same_healthcheck(cfg, image_cfg):
        return {}

    test = _test_list(cfg)
    result: dict[str, Any] = {}
    if test:
        result["health_test"] = test
    if test != ["NONE"]:
        result["healthcheck"] = True
    _put_durations(result, cfg, image_cfg, inherit_matching=inherit_matching)
    return result
