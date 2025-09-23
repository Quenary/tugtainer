import logging
from .base_registry_client import BaseRegistryClient
import aiohttp


class GenericRegistryClient(BaseRegistryClient):
    """For any Docker Registry v2"""

    def __init__(
        self,
        image_spec: str,
        registry_url: str,
        username: str | None = None,
        password: str | None = None,
    ):
        super().__init__(image_spec)
        self.registry_url = registry_url.rstrip("/")
        self.auth = (username, password) if username else None

    async def get_remote_digest(self) -> str | None:
        async with aiohttp.ClientSession() as session:
            try:
                headers = {
                    "Accept": "application/vnd.docker.distribution.manifest.v2+json"
                }
                resp = await session.get(
                    f"{self.registry_url}/v2/{self.image}/manifests/{self.tag}",
                    headers=headers,
                    auth=self.auth,  # pyright: ignore[reportArgumentType]
                )
                if resp.status == 200:
                    return resp.headers.get("Docker-Content-Digest")
                return None
            except Exception as e:
                logging.error(f"Error getting digest of image {self.image_spec}\n{e}")
