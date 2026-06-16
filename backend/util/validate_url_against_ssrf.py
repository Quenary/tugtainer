from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network, ip_address
from typing import Final
from urllib.parse import ParseResult, urlparse

import dns.asyncresolver

from backend.const import RESTRICTED_NETWORKS
from backend.exception import TugUrlValidationError, TugUrlValidationSSRFError


async def validate_url_against_ssrf(
    url: str,
    allowed_networks: set[IPv4Network | IPv6Network],
    allowed_endpoints: set[str],
) -> None:
    """
    Validate URL against SSRF.

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
        return

    resolved: Final[set[IPv4Address | IPv6Address]] = set()

    # Quick way for urls with ips
    try:
        resolved.add(ip_address(hostname))
    except ValueError:
        pass

    # Resolve ip address
    if not resolved:
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

    if not resolved:
        raise TugUrlValidationError(
            f"Failed to resolve hostname '{hostname}' "
            f"while validating '{url}' for SSRF protection"
        )

    for address in resolved:
        if any(address in network for network in allowed_networks):
            return

    for address in resolved:
        if any(address in network for network in RESTRICTED_NETWORKS):
            raise TugUrlValidationSSRFError(
                f"URL '{url}' resolves to a private or reserved address "
                "while validating for SSRF protection"
            )
