import socket
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network, ip_address
from typing import Final
from urllib.parse import ParseResult, urlparse

import dns.asyncresolver

from backend.const import RESTRICTED_NETWORKS
from backend.exception import TugUrlValidationError, TugUrlValidationSSRFError

type ResolvedIp = IPv4Address | IPv6Address


def parse_literal_ip(hostname: str) -> ResolvedIp | None:
    """
    Parse a hostname that is already an IP, including non-canonical IPv4
    forms that ``ip_address()`` rejects but the libc stack accepts
    (decimal ``2886795265``, ``127.1``, octal/hex).
    """
    try:
        return ip_address(hostname)
    except ValueError:
        pass
    try:
        return ip_address(socket.inet_ntoa(socket.inet_aton(hostname)))
    except OSError:
        return None


def is_connect_allowed(
    address: ResolvedIp,
    allowed_networks: set[IPv4Network | IPv6Network],
) -> bool:
    """Whether this address may be used for a subsequent connection."""
    if any(address in network for network in allowed_networks):
        return True
    if any(address in network for network in RESTRICTED_NETWORKS):
        return False
    return True


async def _resolve_hostname(hostname: str) -> set[ResolvedIp]:
    resolved: set[ResolvedIp] = set()
    literal = parse_literal_ip(hostname)
    if literal is not None:
        return {literal}

    try:
        answers = await dns.asyncresolver.resolve(hostname, "A")
        resolved.update(ip_address(rdata.address) for rdata in answers)
    except Exception:
        pass

    try:
        answers = await dns.asyncresolver.resolve(hostname, "AAAA")
        resolved.update(ip_address(rdata.address) for rdata in answers)
    except Exception:
        pass

    return resolved


async def validate_url_against_ssrf(
    url: str,
    allowed_networks: set[IPv4Network | IPv6Network],
    allowed_endpoints: set[str],
) -> set[ResolvedIp]:
    """
    Validate URL against SSRF.

    Returns the addresses that are safe to connect to. An empty set means
    the URL was accepted without a resolved address (allowlisted hostname);
    the caller must resolve and pin separately if it needs a destination.

    Raises TugUrlValidationSSRFError if URL is valid and resolved to ip,
    but not in allowed networks or endpoints.

    Raises TugUrlValidationError if URL missing hostname or cannot be resolved to ip.

    May raise ValueError if URL invalid.
    """
    parsed: Final[ParseResult] = urlparse(url)

    if not parsed.hostname:
        raise TugUrlValidationError(
            f"URL '{url}' does not contain hostname "
            "while validating for SSRF protection"
        )

    hostname: Final = parsed.hostname
    port: Final = parsed.port

    endpoint: Final[str] = f"{hostname}:{port}" if port is not None else hostname

    if endpoint in allowed_endpoints:
        literal = parse_literal_ip(hostname)
        if literal is not None:
            return {literal}
        # Hostname allow-list: skip DNS so a compose name can be saved
        # before it is resolvable. The agent client pins via getaddrinfo.
        return set()

    resolved: Final[set[ResolvedIp]] = await _resolve_hostname(hostname)

    if not resolved:
        raise TugUrlValidationError(
            f"Failed to resolve hostname '{hostname}' "
            f"while validating '{url}' for SSRF protection"
        )

    if any(address in network for address in resolved for network in allowed_networks):
        return {
            address
            for address in resolved
            if is_connect_allowed(address, allowed_networks)
        }

    for address in resolved:
        if any(address in network for network in RESTRICTED_NETWORKS):
            raise TugUrlValidationSSRFError(
                f"URL '{url}' resolves to a private or reserved address "
                "while validating for SSRF protection"
            )

    return resolved
