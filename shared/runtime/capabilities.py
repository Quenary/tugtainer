"""What a Docker or Podman daemon can accept on create and connect.

Docker gates use the negotiated API. Podman uses its engine version and
Libpod API together with the compat API, and never a Docker-only gate.
"""

from dataclasses import dataclass

from packaging import version
from packaging.version import Version

from shared.runtime.runtime_errors import RuntimePreflightError
from shared.runtime.runtime_models import RuntimeVersion

_DOCKER_API: dict[str, str] = {
    "BindOptions.ReadOnlyNonRecursive": "1.44",
    "BindOptions.ReadOnlyForceRecursive": "1.44",
    "VolumeOptions.Subpath": "1.45",
    "TmpfsOptions.Options": "1.46",
    "Image mounts": "1.48",
    "GwPriority": "1.48",
}

# Present on Podman before it advertised Docker API 1.44.
_PODMAN_ENGINE: dict[str, str] = {
    "BindOptions.NonRecursive": "4.1",
    "BindOptions.CreateMountpoint": "4.4",
    "static MAC address": "5.0",
}


@dataclass(frozen=True)
class RuntimeCapabilities:
    runtime_type: str = "docker"
    api_version: str | None = None
    engine_version: str | None = None
    libpod_api_version: str | None = None

    @classmethod
    def docker(cls, api_version: str | None = None) -> "RuntimeCapabilities":
        return cls(runtime_type="docker", api_version=api_version)

    @classmethod
    def from_version(cls, info: RuntimeVersion | None) -> "RuntimeCapabilities":
        if info is None:
            return cls.docker()
        return cls(
            runtime_type=info.runtime_type or "docker",
            api_version=info.negotiated_api or info.api_version,
            engine_version=info.version,
            libpod_api_version=info.libpod_api_version,
        )

    def require(self, feature: str) -> None:
        """Fail closed when this daemon cannot accept ``feature``."""
        if feature in _DOCKER_API:
            self._require_docker(feature, _DOCKER_API[feature])
            return
        if feature in _PODMAN_ENGINE:
            self._require_podman_engine(feature, _PODMAN_ENGINE[feature])
            return
        raise RuntimePreflightError(f"Unknown runtime feature {feature}")

    def _require_docker(self, feature: str, minimum: str) -> None:
        if self.runtime_type == "podman":
            raise RuntimePreflightError(
                f"{feature} is not supported on Podman ({self._podman_description()})"
            )
        parsed = _parse(self.api_version)
        if parsed is not None and parsed >= version.parse(minimum):
            return
        got = str(parsed) if parsed is not None else "unknown"
        raise RuntimePreflightError(
            f"{feature} requires Docker API >= {minimum}, but the target API is {got}"
        )

    def _require_podman_engine(self, feature: str, minimum: str) -> None:
        if self.runtime_type != "podman":
            return
        if self._podman_at_least(minimum):
            return
        raise RuntimePreflightError(
            f"{feature} is not supported on this Podman "
            f"({self._podman_description()}); Podman {minimum} or newer is required"
        )

    def _podman_at_least(self, minimum: str) -> bool:
        floor = version.parse(minimum)
        for raw in (self.engine_version, self.libpod_api_version):
            parsed = _parse(raw)
            if parsed is not None and parsed >= floor:
                return True
        return False

    def _podman_description(self) -> str:
        return (
            f"engine {self.engine_version or 'unknown'}, "
            f"compat API {self.api_version or 'unknown'}, "
            f"libpod {self.libpod_api_version or 'unknown'}"
        )


def _parse(raw: str | None) -> Version | None:
    if not raw:
        return None
    text = raw.removeprefix("/v").removeprefix("v")
    try:
        return version.parse(text)
    except version.InvalidVersion:
        return None
