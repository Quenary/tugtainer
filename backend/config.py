import os
import secrets
from dotenv import load_dotenv
from typing import ClassVar


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

    # OIDC Configuration
    OIDC_ENABLED: ClassVar[bool]
    OIDC_WELL_KNOWN_URL: ClassVar[str]
    OIDC_CLIENT_ID: ClassVar[str]
    OIDC_CLIENT_SECRET: ClassVar[str]
    OIDC_REDIRECT_URI: ClassVar[str]
    OIDC_SCOPES: ClassVar[str]

    @classmethod
    def load(cls):
        if not cls._loaded:
            load_dotenv()
            cls.HOSTNAME = os.getenv("HOSTNAME", "")
            cls.LOG_LEVEL = (
                os.getenv("LOG_LEVEL") or "warning"
            ).upper()
            cls.DISABLE_AUTH = (
                os.getenv("DISABLE_AUTH", "false").lower() == "true"
            )
            cls.JWT_SECRET_KEY = os.getenv(
                "JWT_SECRET_KEY"
            ) or secrets.token_urlsafe(32)
            cls.JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
            cls.ACCESS_TOKEN_LIFETIME_MIN = int(
                os.getenv("ACCESS_TOKEN_LIFETIME_MIN") or 5
            )
            cls.REFRESH_TOKEN_LIFETIME_MIN = int(
                os.getenv("REFRESH_TOKEN_LIFETIME_MIN")
                or 60 * 24 * 30
            )
            cls.DB_URL = (
                os.getenv("DB_URL")
                or "sqlite+aiosqlite:////tugtainer/tugtainer.db"
            )
            cls.DISABLE_PASSWORD = (
                os.getenv("DISABLE_PASSWORD", "false").lower()
                == "true"
            )
            cls.PASSWORD_FILE = (
                os.getenv("PASSWORD_FILE")
                or "/tugtainer/password_hash"
            )
            cls.HTTPS = os.getenv("HTTPS", "false").lower() == "true"
            cls.DOMAIN = os.getenv("DOMAIN")

            # OIDC Configuration
            cls.OIDC_ENABLED = (
                os.getenv("OIDC_ENABLED", "false").lower() == "true"
            )
            cls.OIDC_WELL_KNOWN_URL = os.getenv(
                "OIDC_WELL_KNOWN_URL", ""
            )
            cls.OIDC_CLIENT_ID = os.getenv("OIDC_CLIENT_ID", "")
            cls.OIDC_CLIENT_SECRET = os.getenv(
                "OIDC_CLIENT_SECRET", ""
            )
            cls.OIDC_REDIRECT_URI = os.getenv("OIDC_REDIRECT_URI", "")
            cls.OIDC_SCOPES = os.getenv(
                "OIDC_SCOPES", "openid profile email"
            )


Config.load()
