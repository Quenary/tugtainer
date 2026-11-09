import pytest

from backend.core.container_util.map_healthcheck_to_kwargs import (
    map_healthcheck_to_kwargs,
)
from shared.runtime.runtime_models import (
    ContainerHealthCheck,
)

NS = 1_000_000_000

EXEC_TEST = ["CMD", "/beszel", "health", "--url", "http://127.0.0.1:8090"]
SHELL_TEST = ["CMD-SHELL", "curl -f http://localhost || exit 1"]
QUOTED_TEST = ["CMD", "echo", "hello world", 'say "hi"']


def _hc(
    test: list[str] | None = None,
    interval: int | None = 30 * NS,
    timeout: int | None = 5 * NS,
    retries: int | None = 3,
    start_period: int | None = 10 * NS,
    start_interval: int | None = None,
) -> ContainerHealthCheck:
    return ContainerHealthCheck(
        test=test,
        interval=interval,
        timeout=timeout,
        retries=retries,
        start_period=start_period,
        start_interval=start_interval,
    )


def test_no_healthcheck_without_image_disables():
    assert map_healthcheck_to_kwargs(None) == {"healthcheck": False}


def test_no_healthcheck_matching_empty_image_is_omitted():
    assert map_healthcheck_to_kwargs(None, None, inherit_matching=True) == {}


def test_no_healthcheck_against_image_disables():
    assert map_healthcheck_to_kwargs(
        None, _hc(test=EXEC_TEST), inherit_matching=True
    ) == {"healthcheck": False}


def test_exec_form_matching_image_is_omitted():
    cfg = _hc(test=EXEC_TEST, start_interval=NS)
    assert map_healthcheck_to_kwargs(cfg, cfg, inherit_matching=True) == {}


def test_shell_form_matching_image_is_omitted():
    cfg = _hc(test=SHELL_TEST)
    assert map_healthcheck_to_kwargs(cfg, cfg, inherit_matching=True) == {}


def test_none_matching_image_is_omitted():
    cfg = _hc(
        test=["NONE"], interval=None, timeout=None, retries=None, start_period=None
    )
    assert map_healthcheck_to_kwargs(cfg, cfg, inherit_matching=True) == {}


def test_matching_test_keeps_overridden_interval_with_original_test():
    container = _hc(test=EXEC_TEST, interval=60 * NS)
    image = _hc(test=EXEC_TEST, interval=30 * NS)

    assert map_healthcheck_to_kwargs(container, image, inherit_matching=True) == {
        "healthcheck": True,
        "health_test": EXEC_TEST,
        "health_interval": 60 * NS,
    }


def test_overridden_exec_form_is_verbatim():
    container = _hc(test=QUOTED_TEST)
    image = _hc(test=["CMD", "/other", "health"])

    result = map_healthcheck_to_kwargs(container, image, inherit_matching=True)
    assert result["healthcheck"] is True
    assert result["health_test"] == QUOTED_TEST


def test_explicit_none_disables_when_image_has_a_check():
    container = _hc(
        test=["NONE"], interval=None, timeout=None, retries=None, start_period=None
    )
    image = _hc(test=EXEC_TEST)

    assert map_healthcheck_to_kwargs(container, image, inherit_matching=True) == {
        "health_test": ["NONE"]
    }


def test_subsecond_durations_and_start_interval_are_not_rounded():
    cfg = _hc(
        test=EXEC_TEST,
        interval=500_000_000,
        timeout=250_000_000,
        start_period=1_500_000_000,
        start_interval=750_000_000,
    )

    result = map_healthcheck_to_kwargs(cfg)
    assert result["health_interval"] == 500_000_000
    assert result["health_timeout"] == 250_000_000
    assert result["health_start_period"] == 1_500_000_000
    assert result["health_start_interval"] == 750_000_000


def test_start_interval_override_is_kept_with_original_test():
    container = _hc(test=EXEC_TEST, start_interval=2 * NS)
    image = _hc(test=EXEC_TEST, start_interval=NS)

    result = map_healthcheck_to_kwargs(container, image, inherit_matching=True)
    assert result["health_test"] == EXEC_TEST
    assert result["health_start_interval"] == 2 * NS
    assert "health_interval" not in result


def test_without_image_compare_keeps_verbatim_test_and_nanoseconds():
    cfg = _hc(test=EXEC_TEST, start_interval=NS)

    result = map_healthcheck_to_kwargs(cfg)
    assert result == {
        "healthcheck": True,
        "health_test": EXEC_TEST,
        "health_interval": 30 * NS,
        "health_timeout": 5 * NS,
        "health_retries": 3,
        "health_start_period": 10 * NS,
        "health_start_interval": NS,
    }


@pytest.mark.parametrize(
    "test",
    [EXEC_TEST, SHELL_TEST, QUOTED_TEST, ["NONE"], ["custom", "a b", "c"]],
)
def test_test_list_is_not_flattened(test: list[str]):
    result = map_healthcheck_to_kwargs(_hc(test=test))
    assert result["health_test"] == test
    assert "health_cmd" not in result
