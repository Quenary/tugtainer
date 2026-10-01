import os

import pytest
from pytest_mock import MockerFixture

from agent.config import Config

_CONFIG_FIELDS = (
    "HOSTNAME",
    "LOG_LEVEL",
    "AGENT_SECRET",
    "ALLOW_UNAUTHENTICATED_AGENT",
    "ALLOW_EXEC",
    "AGENT_SIGNATURE_TTL",
    "DOCKER_TIMEOUT",
)

_DEFAULTS = {
    "HOSTNAME": "",
    "LOG_LEVEL": "INFO",
    "AGENT_SECRET": None,
    "ALLOW_UNAUTHENTICATED_AGENT": False,
    "ALLOW_EXEC": False,
    "AGENT_SIGNATURE_TTL": 5,
    "DOCKER_TIMEOUT": 15,
}


@pytest.fixture(autouse=True)
def reset_config_loaded():
    orig_loaded = Config._loaded
    orig_values = {name: getattr(Config, name, None) for name in _CONFIG_FIELDS}
    Config._loaded = False
    yield
    Config._loaded = orig_loaded
    for name, value in orig_values.items():
        setattr(Config, name, value)


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({}, _DEFAULTS),
        (
            {
                "HOSTNAME": "agent-host",
                "LOG_LEVEL": "debug",
                "AGENT_SECRET": "my-secret",
                "ALLOW_UNAUTHENTICATED_AGENT": "true",
                "ALLOW_EXEC": "true",
                "AGENT_SIGNATURE_TTL": "10",
                "DOCKER_TIMEOUT": "30",
            },
            {
                "HOSTNAME": "agent-host",
                "LOG_LEVEL": "DEBUG",
                "AGENT_SECRET": "my-secret",
                "ALLOW_UNAUTHENTICATED_AGENT": True,
                "ALLOW_EXEC": True,
                "AGENT_SIGNATURE_TTL": 10,
                "DOCKER_TIMEOUT": 30,
            },
        ),
        (
            {
                "AGENT_SECRET": "",
                "ALLOW_UNAUTHENTICATED_AGENT": "FALSE",
                "ALLOW_EXEC": "yes",
                "LOG_LEVEL": "",
            },
            _DEFAULTS,
        ),
    ],
)
def test_config_load(
    mocker: MockerFixture,
    env: dict[str, str],
    expected: dict[str, object],
):
    mocker.patch.dict(os.environ, env, clear=True)
    mocker.patch("agent.config.load_dotenv")
    mocker.patch("agent.config.apply_file_env")

    Config.load()

    for key, value in expected.items():
        assert getattr(Config, key) == value
