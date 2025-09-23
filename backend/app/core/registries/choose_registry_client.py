from .dockerhub_registry_client import DockerHubRegistryClient
from .generic_registry_client import GenericRegistryClient
from urllib.parse import urlparse


def choose_registry_client(image_spec: str):
    if "/" not in image_spec or image_spec.startswith("library/"):
        return DockerHubRegistryClient(image_spec)
    if image_spec.startswith("ghcr.io"):
        return GenericRegistryClient(image_spec, "https://ghcr.io")
    # По умолчанию пробуем как generic (например, приватный Harbor/Artifactory)
    parsed = urlparse(image_spec)
    if parsed.netloc:
        return GenericRegistryClient(image_spec, f"https://{parsed.netloc}")
    return DockerHubRegistryClient(image_spec)
