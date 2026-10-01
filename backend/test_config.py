import os
from ipaddress import IPv4Network
from unittest.mock import patch

import pytest

from backend.config import Config
from backend.const import LOCAL_AGENT_ENDPOINT


@pytest.fixture(autouse=True)
def reset_config_loaded():
    # Store original state
    orig_loaded = Config._loaded
    Config._loaded = False

    yield

    # Restore original state
    Config._loaded = orig_loaded


@patch.dict(os.environ, {}, clear=True)
@patch("backend.config.load_dotenv")
@patch("backend.config.apply_file_env")
def test_config_empty_env(mock_apply, mock_load):
    Config.load()

    assert Config.HOSTNAME == ""
    assert Config.LOG_LEVEL == "INFO"
    assert Config.DISABLE_AUTH is False
    assert Config.JWT_ALGORITHM == "HS256"
    assert Config.ACCESS_TOKEN_LIFETIME_MIN == 5
    assert Config.REFRESH_TOKEN_LIFETIME_MIN == 43200
    assert Config.DB_URL == "sqlite+aiosqlite:////tugtainer/tugtainer.db"
    assert Config.DISABLE_PASSWORD is False
    assert Config.HTTPS is False
    assert Config.DOMAIN is None
    assert Config.ALLOW_ORIGINS == []
    assert Config.OIDC_ENABLED is False
    assert Config.AGENT_SECRET is None
    assert Config.AGENT_ENABLED is True
    # If AGENT_ENABLED is true (default), then default endpoint is the local agent
    assert Config.AGENT_ALLOW_ENDPOINTS == {LOCAL_AGENT_ENDPOINT}


@patch.dict(
    os.environ,
    {
        "HOSTNAME": "test-host",
        "LOG_LEVEL": "debug",
        "DISABLE_AUTH": "true",
        "ACCESS_TOKEN_LIFETIME_MIN": "10",
        "REFRESH_TOKEN_LIFETIME_MIN": "60",
        "HTTPS": "true",
        "DOMAIN": "example.com",
        "ALLOW_ORIGINS": "http://localhost:4200, https://ui.example.com",
        "OIDC_ENABLED": "true",
        "OIDC_ALLOWED_EMAILS": "admin@example.com, user@example.com",
        "AGENT_ALLOW_NETWORKS": "192.168.1.0/24, 10.0.0.0/8",
        "AGENT_SECRET": "my-secret",
        "AGENT_ENABLED": "false",
    },
    clear=True,
)
@patch("backend.config.load_dotenv")
@patch("backend.config.apply_file_env")
def test_config_filled_env(mock_apply, mock_load):
    Config.load()

    assert Config.HOSTNAME == "test-host"
    assert Config.LOG_LEVEL == "DEBUG"
    assert Config.DISABLE_AUTH is True
    assert Config.ACCESS_TOKEN_LIFETIME_MIN == 10
    assert Config.REFRESH_TOKEN_LIFETIME_MIN == 60
    assert Config.HTTPS is True
    assert Config.DOMAIN == "example.com"
    assert Config.ALLOW_ORIGINS == ["http://localhost:4200", "https://ui.example.com"]
    assert Config.OIDC_ENABLED is True
    assert Config.OIDC_ALLOWED_EMAILS == {"admin@example.com", "user@example.com"}

    assert len(Config.AGENT_ALLOW_NETWORKS) == 2
    assert IPv4Network("192.168.1.0/24") in Config.AGENT_ALLOW_NETWORKS
    assert IPv4Network("10.0.0.0/8") in Config.AGENT_ALLOW_NETWORKS

    assert Config.AGENT_SECRET == "my-secret"
    assert Config.AGENT_ENABLED is False
    # AGENT_ENABLED is false, so default AGENT_ALLOW_ENDPOINTS is empty
    assert Config.AGENT_ALLOW_ENDPOINTS == set()
