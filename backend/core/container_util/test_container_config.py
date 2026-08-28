import pytest
from python_on_whales.components.container.models import (
    ContainerConfig,
    ContainerHealthCheck,
    ContainerHostConfig,
    ContainerInspectResult,
)
from python_on_whales.components.image.models import ImageInspectResult

from backend.core.container_util.container_config import get_container_config


# Fields mapping generic test case
def test_get_container_config_base_mapping():
    container = ContainerInspectResult(
        name="test-container",
        config=ContainerConfig(
            image="ubuntu:latest", env=["FOO=bar"], labels={"version": "1.0"}
        ),
        host_config=ContainerHostConfig(cap_add=["NET_ADMIN"]),
    )
    res, commands = get_container_config(container, image=None, docker_version=None)

    assert res.name == "test-container"
    assert res.image == "ubuntu:latest"
    assert res.envs == {"FOO": "bar"}
    assert res.labels == {"version": "1.0"}
    assert res.cap_add == ["NET_ADMIN"]
    assert isinstance(commands, list)


# Entrypoint + cmd parametrized test
# Related to #212
@pytest.mark.parametrize(
    "case_name, c_entrypoint, c_cmd, i_entrypoint, i_cmd, expected_entrypoint, expected_cmd",
    [
        (
            "Should drop on exact match",
            ["executable", "--"],
            ["arg1", "arg2"],
            ["executable", "--"],
            ["arg1", "arg2"],
            None,
            None,
        ),
        (
            "Should drop on implicit match",
            ["executable"],
            ["arg1", "arg2"],
            "executable",
            ["arg1", "arg2"],
            None,
            None,
        ),
        (
            "Should unwrap entrypoint list to a string with extra args in cmd",
            ["executable", "--", "arg1"],
            ["arg2", "arg3"],
            None,
            None,
            "executable",
            ["--", "arg1", "arg2", "arg3"],
        ),
        (
            "Should preserve entrypoint and cmd (str, list)",
            "/bin/sh",
            ["-c", "echo 1"],
            None,
            None,
            "/bin/sh",
            ["-c", "echo 1"],
        ),
        (
            "Should preserve if entrypoint changed",
            ["executable1"],
            ["arg1"],
            ["executable2"],
            ["arg1"],
            "executable1",
            ["arg1"],
        ),
        (
            "Should preserve if cmd changed",
            ["executable1"],
            ["arg1"],
            ["executable1"],
            ["arg2"],
            "executable1",
            ["arg1"],
        ),
    ],
)
def test_entrypoint_cmd_logic(
    case_name,
    c_entrypoint,
    c_cmd,
    i_entrypoint,
    i_cmd,
    expected_entrypoint,
    expected_cmd,
):
    container = ContainerInspectResult(
        config=ContainerConfig(image="test_image", entrypoint=c_entrypoint, cmd=c_cmd)
    )
    image = ImageInspectResult(
        config=ContainerConfig(entrypoint=i_entrypoint, cmd=i_cmd)
    )

    res, _ = get_container_config(container, image=image, docker_version=None)

    assert res.entrypoint == expected_entrypoint, f"Failed on: {case_name} (entrypoint)"
    assert res.command == expected_cmd, f"Failed on: {case_name} (command)"


# Related to #226: inherit image healthcheck instead of flattening CMD to CMD-SHELL
_HC_NS = 1_000_000_000
_EXEC_HC = ContainerHealthCheck(
    test=["CMD", "/beszel", "health", "--url", "http://127.0.0.1:8090"],
    interval=30 * _HC_NS,
    timeout=5 * _HC_NS,
    retries=3,
    start_period=10 * _HC_NS,
)


def test_healthcheck_dropped_when_matching_image():
    container = ContainerInspectResult(
        config=ContainerConfig(image="test_image", healthcheck=_EXEC_HC)
    )
    image = ImageInspectResult(
        config=ContainerConfig(healthcheck=_EXEC_HC)
    )

    res, _ = get_container_config(container, image=image, docker_version=None)

    assert res.healthcheck is None
    assert res.health_cmd is None
    assert res.health_interval is None
    assert res.health_timeout is None
    assert res.health_retries is None
    assert res.health_start_period is None


def test_healthcheck_override_keeps_cmd_when_different_from_image():
    container = ContainerInspectResult(
        config=ContainerConfig(image="test_image", healthcheck=_EXEC_HC)
    )
    image = ImageInspectResult(
        config=ContainerConfig(
            healthcheck=ContainerHealthCheck(test=["CMD", "/other", "health"])
        )
    )

    res, _ = get_container_config(container, image=image, docker_version=None)

    assert res.healthcheck is True
    assert res.health_cmd == "/beszel health --url http://127.0.0.1:8090"


# workdir parametrized test
@pytest.mark.parametrize(
    "c_workdir, i_workdir, expected_workdir",
    [
        ("/app", "/app", None),  # drop matched
        ("/app", "/root", "/app"),  # preserve changed
    ],
)
def test_workdir_logic(c_workdir, i_workdir, expected_workdir):
    container = ContainerInspectResult(
        config=ContainerConfig(image="test_image", working_dir=c_workdir)
    )
    image = ImageInspectResult(config=ContainerConfig(working_dir=i_workdir))

    res, _ = get_container_config(container, image=image, docker_version=None)

    assert res.workdir == expected_workdir


# Podman inspect returns "private" for default UTS/userns modes;
# Docker CLI only accepts "" or "host" (#220).
@pytest.mark.parametrize(
    "uts_mode, userns_mode, expected_uts, expected_userns",
    [
        ("private", "private", None, None),
        ("host", "host", "host", "host"),
        ("", "", None, None),
        (None, None, None, None),
        ("private", "host", None, "host"),
        ("host", "private", "host", None),
    ],
)
def test_uts_userns_ns_mode_normalization(
    uts_mode, userns_mode, expected_uts, expected_userns
):
    container = ContainerInspectResult(
        config=ContainerConfig(image="test_image"),
        host_config=ContainerHostConfig(
            uts_mode=uts_mode, userns_mode=userns_mode
        ),
    )

    res, _ = get_container_config(container, image=None, docker_version=None)

    assert res.uts == expected_uts
    assert res.userns == expected_userns


# Docker CLI refuses only labels with empty or whitespaced keys,
# anything else must be preserved (#193)
def test_labels_rejected_by_cli_are_dropped():
    container = ContainerInspectResult(
        config=ContainerConfig(
            image="test_image",
            labels={
                "homepage.group": "Infra",
                "pangolin.public-resources.ntfy.rules[0].action": "pass",
                "ru.название": "значение",
                "with.value": "value with spaces",
                "* Regular Improvements": "",
                "tab\tkey": "1",
                "": "no key",
            },
        )
    )

    res, _ = get_container_config(container, image=None, docker_version=None)

    assert res.labels == {
        "homepage.group": "Infra",
        "pangolin.public-resources.ntfy.rules[0].action": "pass",
        "ru.название": "значение",
        "with.value": "value with spaces",
    }
