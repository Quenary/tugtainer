import os
from dotenv import load_dotenv
from typing import ClassVar


class Config:
    _loaded: ClassVar[bool] = False

    HOSTNAME: ClassVar[str]
    LOG_LEVEL: ClassVar[str]
    AGENT_SECRET: ClassVar[str | None]
    AGENT_SIGNATURE_LIFETIME: ClassVar[int]
    DOCKER_TIMEOUT: ClassVar[int]
    DOCKER_HOST: ClassVar[str | None]

    @classmethod
    def load(cls):
        if not cls._loaded:
            load_dotenv()
            cls.HOSTNAME = os.getenv("HOSTNAME", "")
            cls.LOG_LEVEL = (
                os.getenv("LOG_LEVEL") or "warning"
            ).upper()
            cls.AGENT_SECRET = os.getenv("AGENT_SECRET") or None
            cls.AGENT_SIGNATURE_LIFETIME = int(
                os.getenv("AGENT_SIGNATURE_LIFETIME") or 10
            )
            cls.DOCKER_TIMEOUT = int(
                os.getenv("DOCKER_TIMEOUT") or 15
            )
            cls.DOCKER_HOST = os.getenv("DOCKER_HOST") or None


Config.load()
