import socket
from ipaddress import ip_address
from unittest.mock import AsyncMock, patch

import pytest

from backend.exception import TugUrlValidationSSRFError
from backend.util.pinned_ip_resolver import (
    PinnedIpResolver,
    resolve_host_ips,
    resolve_results_for_ips,
)


@pytest.mark.asyncio
async def test_resolver_returns_validated_ipv4_and_ipv6():
    resolver = PinnedIpResolver("https://agent.example.com:9413")
    pinned = {ip_address("203.0.113.10"), ip_address("2001:db8::10")}
    with patch(
        "backend.util.pinned_ip_resolver.validate_url_against_ssrf",
        new=AsyncMock(return_value=pinned),
    ):
        ipv4 = await resolver.resolve("agent.example.com", 9413, socket.AF_INET)
        ipv6 = await resolver.resolve("AGENT.example.com", 9413, socket.AF_INET6)
        any_family = await resolver.resolve(
            "agent.example.com", 9413, socket.AF_UNSPEC
        )
    await resolver.close()

    assert ipv4 == [
        {
            "hostname": "agent.example.com",
            "host": "203.0.113.10",
            "port": 9413,
            "family": socket.AF_INET,
            "proto": 0,
            "flags": socket.AI_NUMERICHOST,
        }
    ]
    assert ipv6[0]["host"] == "2001:db8::10"
    assert {item["host"] for item in any_family} == {
        "203.0.113.10",
        "2001:db8::10",
    }


@pytest.mark.asyncio
async def test_resolver_fails_closed_when_validation_rejects():
    resolver = PinnedIpResolver("https://agent.example.com")
    with (
        patch(
            "backend.util.pinned_ip_resolver.validate_url_against_ssrf",
            new=AsyncMock(side_effect=TugUrlValidationSSRFError("restricted")),
        ),
        pytest.raises(OSError, match="restricted"),
    ):
        await resolver.resolve("agent.example.com", 9413, socket.AF_INET)
    await resolver.close()


@pytest.mark.asyncio
async def test_resolver_fails_closed_without_addresses():
    resolver = PinnedIpResolver("https://agent.example.com")
    with (
        patch(
            "backend.util.pinned_ip_resolver.validate_url_against_ssrf",
            new=AsyncMock(return_value=set()),
        ),
        patch(
            "backend.util.pinned_ip_resolver.resolve_host_ips",
            new=AsyncMock(return_value=set()),
        ),
        pytest.raises(OSError, match="No validated address"),
    ):
        await resolver.resolve("agent.example.com", 9413, socket.AF_INET)
    await resolver.close()


@pytest.mark.asyncio
async def test_allowlisted_hostname_pins_getaddrinfo_ips():
    resolver = PinnedIpResolver("http://tugtainer-agent:8001")
    with (
        patch(
            "backend.util.pinned_ip_resolver.validate_url_against_ssrf",
            new=AsyncMock(return_value=set()),
        ),
        patch(
            "backend.util.pinned_ip_resolver.resolve_host_ips",
            new=AsyncMock(return_value={ip_address("172.18.0.4")}),
        ),
    ):
        result = await resolver.resolve("tugtainer-agent", 8001, socket.AF_INET)
    await resolver.close()

    assert [item["host"] for item in result] == ["172.18.0.4"]


@pytest.mark.asyncio
async def test_resolver_uses_fallback_for_other_hosts():
    resolver = PinnedIpResolver("https://agent.example.com")
    fallback = [
        {
            "hostname": "proxy.example.com",
            "host": "198.51.100.1",
            "port": 8080,
            "family": socket.AF_INET,
            "proto": 0,
            "flags": 0,
        }
    ]
    with patch.object(
        resolver._fallback, "resolve", new=AsyncMock(return_value=fallback)
    ) as mock_resolve:
        result = await resolver.resolve("proxy.example.com", 8080, socket.AF_INET)
    await resolver.close()

    assert result == fallback
    mock_resolve.assert_awaited_once()


def test_resolve_results_filters_family():
    results = resolve_results_for_ips(
        "agent.example.com",
        80,
        socket.AF_INET,
        {ip_address("203.0.113.10"), ip_address("2001:db8::1")},
    )
    assert [item["host"] for item in results] == ["203.0.113.10"]


@pytest.mark.asyncio
async def test_resolve_host_ips_reads_getaddrinfo():
    gai = (
        (
            socket.AF_INET,
            socket.SOCK_STREAM,
            0,
            "",
            ("172.18.0.4", 0),
        ),
    )
    with patch(
        "backend.util.pinned_ip_resolver.asyncio.get_running_loop"
    ) as mock_loop:
        loop = mock_loop.return_value
        loop.getaddrinfo = AsyncMock(return_value=gai)
        result = await resolve_host_ips("tugtainer-agent")

    assert result == {ip_address("172.18.0.4")}
