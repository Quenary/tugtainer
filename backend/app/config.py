import os
import secrets
from dotenv import load_dotenv
from typing import ClassVar


class Config:
    _loaded: ClassVar[bool] = False

    LOG_LEVEL: ClassVar[str]
    JWT_SECRET_KEY: ClassVar[str | bytes]
    JWT_ALGORITHM: ClassVar[str]
    ACCESS_TOKEN_LIFETIME_MIN: ClassVar[int]
    REFRESH_TOKEN_LIFETIME_MIN: ClassVar[int]
    DB_URL: ClassVar[str]
    PASSWORD_FILE: ClassVar[str]

    @classmethod
    def load(cls):
        if not cls._loaded:
            load_dotenv()
            cls.LOG_LEVEL = (os.getenv("LOG_LEVEL") or "warning").upper()
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
                os.getenv("DB_URL")
                or "sqlite+aiosqlite:////dockobserver/dockobserver.db"
            )
            cls.PASSWORD_FILE = (
                os.getenv("PASSWORD_FILE") or "/dockobserver/password_hash"
            )


Config.load()
