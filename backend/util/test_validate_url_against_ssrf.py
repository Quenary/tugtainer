from ipaddress import ip_network
from unittest.mock import AsyncMock, patch

import pytest

from backend.exception import TugUrlValidationError, TugUrlValidationSSRFError
from backend.util.validate_url_against_ssrf import validate_url_against_ssrf


@pytest.fixture
def allowed_networks():
    # Intentionally overlapping with restricted private network 192.168.0.0/16
    return {ip_network("192.168.1.0/24")}


@pytest.fixture
def allowed_endpoints():
    # Intentionally using a hostname that might resolve to a restricted IP
    return {"internal-service.local", "127.0.0.1:8080"}


@pytest.mark.asyncio
class TestValidateUrlAgainstSsrf:
    @pytest.mark.parametrize(
        "url",
        [
            "somestring",
            "http://",
            "file:///etc/passwd",
            "///just/path",
        ],
    )
    async def test_invalid_url_structure_raises_validation_error(
        self, url, allowed_networks, allowed_endpoints
    ):
        # URLs missing a valid hostname must raise TugUrlValidationError
        with pytest.raises(TugUrlValidationError, match="does not contain hostname"):
            await validate_url_against_ssrf(
                url=url,
                allowed_networks=allowed_networks,
                allowed_endpoints=allowed_endpoints,
            )

    @pytest.mark.parametrize(
        "url",
        [
            "https://internal-service.local/api/v1",
            "http://127.0.0.1:8080/metrics",
        ],
    )
    async def test_allowed_endpoints_pass_without_dns(
        self, url, allowed_networks, allowed_endpoints
    ):
        # Whitelisted endpoints must bypass DNS resolution and return successfully
        with patch("dns.asyncresolver.resolve") as mock_resolve:
            await validate_url_against_ssrf(
                url=url,
                allowed_networks=allowed_networks,
                allowed_endpoints=allowed_endpoints,
            )
            mock_resolve.assert_not_called()

    @pytest.mark.parametrize(
        "url, expected_exception",
        [
            # Allowed sub-network within a restricted range (192.168.1.0/24 inside 192.168.0.0/16)
            ("http://192.168.1.50/status", None),
            # Explicitly restricted network outside the allowed subset
            ("https://192.168.2.50", TugUrlValidationSSRFError),
            # Another default restricted local host range
            ("http://127.0.0.1", TugUrlValidationSSRFError),
            # Public safe IP not present in restricted networks
            ("http://8.8.8.8", None),
        ],
    )
    async def test_ip_addresses_handling(
        self, url, expected_exception, allowed_networks, allowed_endpoints
    ):
        # Direct IP validation matching allowed exceptions vs restricted defaults
        if expected_exception:
            with pytest.raises(expected_exception):
                await validate_url_against_ssrf(
                    url, allowed_networks, allowed_endpoints
                )
        else:
            await validate_url_against_ssrf(url, allowed_networks, allowed_endpoints)

    @pytest.mark.parametrize(
        "resolved_ips, expected_exception",
        [
            # DNS resolves to the explicit whitelisted private subnet exception
            (["192.168.1.10"], None),
            # DNS resolves to a standard restricted private network IP
            (["10.0.0.1"], TugUrlValidationSSRFError),
            # DNS resolves to a restricted IPv6 loopback address
            (["::1"], TugUrlValidationSSRFError),
        ],
    )
    @patch("dns.asyncresolver.resolve")
    async def test_dns_resolving_behavior(
        self,
        mock_resolve,
        resolved_ips,
        expected_exception,
        allowed_networks,
        allowed_endpoints,
    ):
        # Dynamic DNS mapping verification for whitelisted vs restricted targets
        mock_answers = []
        for ip in resolved_ips:
            mock_rdata = AsyncMock()
            mock_rdata.address = ip
            mock_answers.append(mock_rdata)

        mock_resolve.return_value = mock_answers

        if expected_exception:
            with pytest.raises(expected_exception):
                await validate_url_against_ssrf(
                    "http://dynamic-target.local", allowed_networks, allowed_endpoints
                )
        else:
            await validate_url_against_ssrf(
                "http://dynamic-target.local", allowed_networks, allowed_endpoints
            )

    @patch("dns.asyncresolver.resolve")
    async def test_dns_resolve_failure_raises_validation_error(
        self, mock_resolve, allowed_networks, allowed_endpoints
    ):
        # Hostnames failing DNS resolution completely must trigger validation errors
        mock_resolve.side_effect = Exception("DNS NXDOMAIN")

        with pytest.raises(TugUrlValidationError, match="Failed to resolve hostname"):
            await validate_url_against_ssrf(
                url="http://unresolved-domain-error.xyz",
                allowed_networks=allowed_networks,
                allowed_endpoints=allowed_endpoints,
            )
