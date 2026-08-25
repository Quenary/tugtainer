import asyncio
import socket
from collections.abc import Iterable
from ipaddress import IPv6Address, ip_address
from typing import Final
from urllib.parse import urlparse

from aiohttp.abc import AbstractResolver, ResolveResult
from aiohttp.resolver import DefaultResolver

from backend.config import Config
from backend.exception import TugUrlValidationError, TugUrlValidationSSRFError
from backend.util.validate_url_against_ssrf import (
    ResolvedIp,
    validate_url_against_ssrf,
)


def resolve_results_for_ips(
    host: str,
    port: int,
    family: socket.AddressFamily | int,
    addresses: Iterable[ResolvedIp],
) -> list[ResolveResult]:
    """Build aiohttp ResolveResult entries for already-validated IPs."""
    results: list[ResolveResult] = []
    for address in addresses:
        address_family = (
            socket.AF_INET6 if isinstance(address, IPv6Address) else socket.AF_INET
        )
        if family not in (0, socket.AF_UNSPEC, address_family):
            continue
        results.append(
            {
                "hostname": host,
                "host": address.compressed,
                "port": port,
                "family": address_family,
                "proto": 0,
                "flags": socket.AI_NUMERICHOST,
            }
        )
    return results


async def resolve_host_ips(hostname: str) -> set[ResolvedIp]:
    """
    Resolve hostname the same way aiohttp's default resolver would
    (getaddrinfo: /etc/hosts, Docker DNS). Used when the SSRF check
    accepted an allowlisted hostname without a DNS result.
    """
    resolved: set[ResolvedIp] = set()
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(
            hostname,
            None,
            type=socket.SOCK_STREAM,
        )
    except OSError:
        return resolved

    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        try:
            resolved.add(ip_address(sockaddr[0]))
        except ValueError:
            continue
    return resolved


class PinnedIpResolver(AbstractResolver):
    """
    Resolve the agent hostname only to IPs that pass SSRF validation.

    Other names (HTTP proxy via trust_env) use the default resolver.
    """

    def __init__(self, url: str):
        self._url: Final = url
        self._hostname: Final = (urlparse(url).hostname or "").casefold()
        self._fallback: Final = DefaultResolver()

    async def resolve(
        self,
        host: str,
        port: int = 0,
        family: socket.AddressFamily = socket.AF_INET,
    ) -> list[ResolveResult]:
        if host.casefold() != self._hostname:
            return await self._fallback.resolve(host, port, family)

        pinned = await self._validated_ips()
        results = resolve_results_for_ips(host, port, family, pinned)
        if not results:
            raise OSError(
                socket.EAI_NONAME,
                f"No validated address to connect to for '{host}'",
            )
        return results

    async def _validated_ips(self) -> set[ResolvedIp]:
        try:
            pinned = await validate_url_against_ssrf(
                self._url,
                Config.AGENT_ALLOW_NETWORKS,
                Config.AGENT_ALLOW_ENDPOINTS,
            )
        except (TugUrlValidationError, TugUrlValidationSSRFError) as e:
            raise OSError(socket.EAI_NONAME, str(e)) from e

        if pinned or not self._hostname:
            return pinned
        return await resolve_host_ips(self._hostname)

    async def close(self) -> None:
        await self._fallback.close()
