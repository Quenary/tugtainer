import logging
import os
import secrets
from ipaddress import IPv4Network, IPv6Network, ip_network
from typing import ClassVar

from dotenv import load_dotenv

from shared.util.file_env import apply_file_env


class Config:
    _loaded: ClassVar[bool] = False

    HOSTNAME: ClassVar[str]
    LOG_LEVEL: ClassVar[str]
    DISABLE_AUTH: ClassVar[bool]
    JWT_SECRET_KEY: ClassVar[str | bytes]
    JWT_ALGORITHM: ClassVar[str]
    ACCESS_TOKEN_LIFETIME_MIN: ClassVar[int]
    REFRESH_TOKEN_LIFETIME_MIN: ClassVar[int]
    DB_URL: ClassVar[str]
    DISABLE_PASSWORD: ClassVar[bool]
    PASSWORD_FILE: ClassVar[str]
    HTTPS: ClassVar[bool]
    DOMAIN: ClassVar[str | None]
    ENABLE_PUBLIC_API: ClassVar[bool]
    ALLOW_HOOKS: ClassVar[bool]
    GH_TOKEN: ClassVar[str]
    DOCKER_CONFIG: ClassVar[str]

    # OIDC Configuration
    OIDC_ENABLED: ClassVar[bool]
    OIDC_WELL_KNOWN_URL: ClassVar[str]
    OIDC_CLIENT_ID: ClassVar[str]
    OIDC_CLIENT_SECRET: ClassVar[str]
    OIDC_REDIRECT_URI: ClassVar[str]
    OIDC_SCOPES: ClassVar[str]
    OIDC_ALLOWED_EMAILS: ClassVar[set[str]]
    OIDC_ALLOWED_SUBJECTS: ClassVar[set[str]]

    # Network security
    NOTIFICATION_ALLOW_SCHEMES: ClassVar[set[str]]
    NOTIFICATION_ALLOW_NETWORKS: ClassVar[set[IPv4Network | IPv6Network]]
    NOTIFICATION_ALLOW_ENDPOINTS: ClassVar[set[str]]
    AGENT_ALLOW_NETWORKS: ClassVar[set[IPv4Network | IPv6Network]]
    AGENT_ALLOW_ENDPOINTS: ClassVar[set[str]]

    @classmethod
    def load(cls):
        if not cls._loaded:
            load_dotenv()
            apply_file_env()
            cls.HOSTNAME = os.getenv("HOSTNAME", "")
            cls.LOG_LEVEL = (os.getenv("LOG_LEVEL") or "info").upper()
            cls.DISABLE_AUTH = os.getenv("DISABLE_AUTH", "false").lower() == "true"
            cls.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or secrets.token_urlsafe(
                32
            )
            cls.JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
            cls.ACCESS_TOKEN_LIFETIME_MIN = int(
                os.getenv("ACCESS_TOKEN_LIFETIME_MIN") or 5
            )
            cls.REFRESH_TOKEN_LIFETIME_MIN = int(
                os.getenv("REFRESH_TOKEN_LIFETIME_MIN") or 60 * 24 * 30
            )
            cls.DB_URL = (
                os.getenv("DB_URL") or "sqlite+aiosqlite:////tugtainer/tugtainer.db"
            )
            cls.DISABLE_PASSWORD = (
                os.getenv("DISABLE_PASSWORD", "false").lower() == "true"
            )
            cls.PASSWORD_FILE = os.getenv("PASSWORD_FILE") or "/tugtainer/password_hash"
            cls.HTTPS = os.getenv("HTTPS", "false").lower() == "true"
            cls.DOMAIN = os.getenv("DOMAIN") or None
            cls.ENABLE_PUBLIC_API = (
                os.getenv("ENABLE_PUBLIC_API", "false").lower() == "true"
            )
            cls.ALLOW_HOOKS = os.getenv("ALLOW_HOOKS", "false").lower() == "true"
            cls.GH_TOKEN = os.getenv("GH_TOKEN", "")
            cls.DOCKER_CONFIG = os.getenv("DOCKER_CONFIG", "~/.docker")

            # OIDC Configuration
            cls.OIDC_ENABLED = os.getenv("OIDC_ENABLED", "false").lower() == "true"
            cls.OIDC_WELL_KNOWN_URL = os.getenv("OIDC_WELL_KNOWN_URL", "")
            cls.OIDC_CLIENT_ID = os.getenv("OIDC_CLIENT_ID", "")
            cls.OIDC_CLIENT_SECRET = os.getenv("OIDC_CLIENT_SECRET", "")
            cls.OIDC_REDIRECT_URI = os.getenv("OIDC_REDIRECT_URI", "")
            cls.OIDC_SCOPES = os.getenv("OIDC_SCOPES", "openid profile email")

            def _parse_set(value: str) -> set[str]:
                return {item.strip() for item in value.split(",") if item.strip()}

            def _parse_env_set(name: str) -> set[str]:
                return _parse_set(os.getenv(name, ""))

            cls.OIDC_ALLOWED_EMAILS = {
                email.casefold() for email in _parse_env_set("OIDC_ALLOWED_EMAILS")
            }
            cls.OIDC_ALLOWED_SUBJECTS = _parse_env_set("OIDC_ALLOWED_SUBJECTS")

            def _parse_networks(name: str) -> set[IPv4Network | IPv6Network]:
                networks = _parse_env_set(name)
                res: set[IPv4Network | IPv6Network] = set()
                for net in networks:
                    try:
                        res.add(ip_network(net))
                    except Exception:
                        logging.warning(
                            f"{net} is not a valid IP network. Check the {name} environment variable."
                        )
                return res

            cls.NOTIFICATION_ALLOW_SCHEMES = _parse_env_set(
                "NOTIFICATION_ALLOW_SCHEMES"
            )
            cls.NOTIFICATION_ALLOW_NETWORKS = _parse_networks(
                "NOTIFICATION_ALLOW_NETWORKS"
            )
            cls.NOTIFICATION_ALLOW_ENDPOINTS = _parse_env_set(
                "NOTIFICATION_ALLOW_ENDPOINTS"
            )
            cls.AGENT_ALLOW_NETWORKS = _parse_networks("AGENT_ALLOW_NETWORKS")
            agent_enabled = os.getenv("AGENT_ENABLED", "true").lower() == "true"
            agent_allow_endpoints = os.getenv("AGENT_ALLOW_ENDPOINTS")
            if agent_allow_endpoints is None:
                agent_allow_endpoints = "127.0.0.1:8001" if agent_enabled else ""
            cls.AGENT_ALLOW_ENDPOINTS = _parse_set(agent_allow_endpoints)


Config.load()
