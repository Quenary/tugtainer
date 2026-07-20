import pytest
from python_on_whales.components.container.models import (
    ContainerConfig,
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
