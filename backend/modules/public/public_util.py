from typing import Any
import aiohttp
from backend.config import Config


async def fetch_latest_release() -> dict[str, Any]:
    url = "https://api.github.com/repos/quenary/tugtainer/releases/latest"
    headers: dict[str, str] = {}
    if Config.GH_TOKEN:
        headers["Authorization"] = f"Bearer {Config.GH_TOKEN}"
    async with aiohttp.ClientSession(
        headers=headers,
        timeout=aiohttp.ClientTimeout(15),
        trust_env=True,
    ) as session:
        async with session.request(
            "GET",
            url,
        ) as res:
            res.raise_for_status()
            return await res.json()
