from .dockerhub_registry_client import DockerHubRegistryClient
from .generic_registry_client import GenericRegistryClient
from urllib.parse import urlparse


def choose_registry_client(image_spec: str):
    parts = image_spec.split("/")

    if len(parts) == 1 or (
        len(parts) == 2
        and not "." in parts[0]
        and not ":" in parts[0]
    ):
        return DockerHubRegistryClient(image_spec)

    registry_host = parts[0]
    if "." in registry_host or ":" in registry_host:
        if registry_host == "ghcr.io":
            return GenericRegistryClient(
                image_spec, "https://ghcr.io"
            )
        elif registry_host == "quay.io":
            return GenericRegistryClient(
                image_spec, "https://quay.io"
            )
        else:
            return GenericRegistryClient(
                image_spec, f"https://{registry_host}"
            )

    return DockerHubRegistryClient(image_spec)
