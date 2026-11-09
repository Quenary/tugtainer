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
        entry = self._auth_entry(registry)
        if not entry or "auth" not in entry:
            return None
        auth = entry["auth"]
        return auth if isinstance(auth, str) else None

    def get_identity_token(self, registry: str) -> str | None:
        """
        OAuth refresh token from an auths entry, as written by ``docker login``.

        When this is set it is the registry credential. Username and password
        on the same entry are not used.
        """
        entry = self._auth_entry(registry)
        if not entry:
            return None
        token = entry.get("identitytoken")
        if isinstance(token, str) and token.strip():
            return token.strip()
        return None

    def _auth_entry(self, registry: str) -> dict[str, Any] | None:
        target = normalize_registry_host(registry)
        if not target:
            return None
        for key, entry in self.auths.items():
            if normalize_registry_host(key) != target:
                continue
            if isinstance(entry, dict):
                return entry
            return None
        return None
