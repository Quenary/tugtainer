import logging
from .base_registry_client import BaseRegistryClient
import aiohttp


class DockerHubRegistryClient(BaseRegistryClient):
    async def get_remote_digest(self) -> str | None:
        async with aiohttp.ClientSession() as session:
            try:
                token_resp = await session.get(
                    "https://auth.docker.io/token",
                    params={
                        "service": "registry.docker.io",
                        "scope": f"repository:{self.image}:pull",
                    },
                )
                token_resp_json: dict[str, str] = await token_resp.json()
                token = token_resp_json.get("token")
                headers = {
                    "Accept": "application/vnd.docker.distribution.manifest.v2+json",
                    "Authorization": f"Bearer {token}",
                }
                resp = await session.get(
                    f"https://registry-1.docker.io/v2/{self.image}/manifests/{self.tag}",
                    headers=headers,
                )
                if resp.status == 200:
                    return resp.headers.get("Docker-Content-Digest")
                return None
            except Exception as e:
                logging.error(f"Error getting digest of image {self.image_spec}\n{e}")
