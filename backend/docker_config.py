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
                with open(self.path, "r") as f:
                    logging.info(
                        f"Docker config loaded successfully from {self.path}"
                    )
                    self.data = json.load(f)
            else:
                logging.warning(
                    f"Missing docker config file: {self.path}"
                )
        except Exception:
            logging.exception(
                f"Error loading docker config file: {self.path}"
            )
        self.auths = self.data.get("auths", {})

    def get_basic_token(self, registry: str) -> str | None:
        """
        Get Basic auth token for registry
        """

        entry = self.auths.get(registry)

        # dockerhub special case
        if not entry:
            if registry in ["registry-1.docker.io", "docker.io"]:
                registry = "https://index.docker.io/v1/"
                entry = self.auths.get(registry)

        # find by partial match
        if not entry:
            for k, v in self.auths.items():
                if registry in k or k in registry:
                    entry = v
                    break

        if not entry:
            return None

        if "auth" in entry:
            return entry["auth"]

        return None
