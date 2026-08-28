import pytest
from python_on_whales.components.container.models import (
    ContainerHealthCheck,
)

from backend.core.container_util.map_healthcheck_to_kwargs import (
    map_healthcheck_to_kwargs,
)

NS = 1_000_000_000

EXEC_TEST = ["CMD", "/beszel", "health", "--url", "http://127.0.0.1:8090"]
SHELL_TEST = ["CMD-SHELL", "curl -f http://localhost || exit 1"]


def _hc(
    test: list[str] | None = None,
    interval: int | None = 30 * NS,
    timeout: int | None = 5 * NS,
    retries: int | None = 3,
    start_period: int | None = 10 * NS,
) -> ContainerHealthCheck:
    return ContainerHealthCheck(
        test=test,
        interval=interval,
        timeout=timeout,
        retries=retries,
        start_period=start_period,
    )


def test_no_healthcheck_without_image_disables():
    assert map_healthcheck_to_kwargs(None) == {"healthcheck": False}


def test_no_healthcheck_matching_empty_image_is_omitted():
    assert (
        map_healthcheck_to_kwargs(None, None, inherit_matching=True) == {}
    )


def test_no_healthcheck_against_image_disables():
    assert map_healthcheck_to_kwargs(
        None, _hc(test=EXEC_TEST), inherit_matching=True
    ) == {"healthcheck": False}


def test_exec_form_matching_image_is_omitted():
    cfg = _hc(test=EXEC_TEST)
    assert map_healthcheck_to_kwargs(cfg, cfg, inherit_matching=True) == {}


def test_shell_form_matching_image_is_omitted():
    cfg = _hc(test=SHELL_TEST)
    assert map_healthcheck_to_kwargs(cfg, cfg, inherit_matching=True) == {}


def test_matching_test_keeps_overridden_interval():
    container = _hc(test=EXEC_TEST, interval=60 * NS)
    image = _hc(test=EXEC_TEST, interval=30 * NS)

    assert map_healthcheck_to_kwargs(
        container, image, inherit_matching=True
    ) == {"health_interval": 60}


def test_overridden_exec_form_is_flattened():
    container = _hc(test=EXEC_TEST)
    image = _hc(test=["CMD", "/other", "health"])

    result = map_healthcheck_to_kwargs(
        container, image, inherit_matching=True
    )
    assert result["healthcheck"] is True
    assert result["health_cmd"] == (
        "/beszel health --url http://127.0.0.1:8090"
    )


def test_without_image_compare_keeps_current_mapping():
    cfg = _hc(test=EXEC_TEST)

    result = map_healthcheck_to_kwargs(cfg)
    assert result == {
        "healthcheck": True,
        "health_cmd": "/beszel health --url http://127.0.0.1:8090",
        "health_interval": 30,
        "health_timeout": 5,
        "health_retries": 3,
        "health_start_period": 10,
    }


@pytest.mark.parametrize(
    "test, expected_cmd",
    [
        (EXEC_TEST, "/beszel health --url http://127.0.0.1:8090"),
        (SHELL_TEST, "curl -f http://localhost || exit 1"),
        (["custom", "a", "b"], "custom a b"),
    ],
)
def test_health_cmd_flattening(test, expected_cmd):
    result = map_healthcheck_to_kwargs(_hc(test=test))
    assert result["health_cmd"] == expected_cmd
