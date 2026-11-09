import json
import logging
from pathlib import Path
from typing import Any

from backend.config import Config
from shared.runtime.registry_auth import normalize_registry_host

__all__ = ["DockerConfig", "normalize_registry_host"]


class DockerConfig:
    """
    Wrapper around the docker config file.
    """

    _instance = None
    path: Path
    data: dict[str, Any]
    auths: dict[str, Any]

    def __new__(cls, path: str = Config.DOCKER_CONFIG):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load(path)
        return cls._instance

    def _load(self, path: str):
        self.path = Path(path).expanduser() / "config.json"
        self.data = {}
        try:
            if self.path.exists():
                with open(self.path) as f:
                    logging.info(f"Docker config loaded successfully from {self.path}")
                    self.data = json.load(f)
            else:
                logging.warning(f"Missing docker config file: {self.path}")
        except Exception:
            logging.exception(f"Error loading docker config file: {self.path}")
        self.auths = self.data.get("auths", {})

    def get_basic_token(self, registry: str) -> str | None:
        """
        Get Basic auth token for registry using exact normalized host match.
        """
        target = normalize_registry_host(registry)
        if not target:
            return None

        for key, entry in self.auths.items():
            if normalize_registry_host(key) != target:
                continue
            if entry and "auth" in entry:
                return entry["auth"]
            return None

        return None
