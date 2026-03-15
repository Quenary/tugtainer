import json
import logging
from pathlib import Path
from typing import Any

from backend.config import Config


class DockerConfig:
    """
    Wrapper around the docker config file.
    """

    _instance = None
    path: Path
    data: dict[str, Any]
    auths: dict[str, Any]

    def __new__(cls, path: str = Config.DOCKER_CONFIG_PATH):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load(path)
        return cls._instance

    def _load(self, path: str):
        self.path = Path(path).expanduser() / "config.json"
        self.data = {}
        try:
            if self.path.exists():
                with open(self.path, "r") as f:
                    self.data = json.load(f)
        except Exception as e:
            logging.error(f"Error loading docker config file: {path}")
            logging.exception(e)
        self.auths = self.data.get("auths", {})

    def get_basic_token(self, registry: str) -> str | None:
        """
        Get Basic auth token for registry
        """

        # dockerhub special case
        if registry in ["registry-1.docker.io", "docker.io"]:
            registry = "https://index.docker.io/v1/"

        entry = self.auths.get(registry)

        if not entry:
            return None

        if "auth" in entry:
            return entry["auth"]

        return None
