import os
from typing import ClassVar

from dotenv import load_dotenv


class Config:
    _loaded: ClassVar[bool] = False

    HOSTNAME: ClassVar[str]
    LOG_LEVEL: ClassVar[str]
    AGENT_SECRET: ClassVar[str | None]
    AGENT_SIGNATURE_TTL: ClassVar[int]
    DOCKER_TIMEOUT: ClassVar[int]

    @classmethod
    def load(cls):
        if not cls._loaded:
            load_dotenv()
            cls.HOSTNAME = os.getenv("HOSTNAME", "")
            cls.LOG_LEVEL = (
                os.getenv("LOG_LEVEL") or "info"
            ).upper()
            cls.AGENT_SECRET = os.getenv("AGENT_SECRET") or None
            cls.AGENT_SIGNATURE_TTL = int(
                os.getenv("AGENT_SIGNATURE_TTL") or 5
            )
            cls.DOCKER_TIMEOUT = int(
                os.getenv("DOCKER_TIMEOUT") or 15
            )


Config.load()
