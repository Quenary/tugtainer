import pytest
from pydantic import ValidationError

from backend.modules.hosts.hosts_model import HostsModel
from backend.modules.hosts.hosts_schemas import HostCreate, HostInfo, HostUpdate

TEST_CA_PEM = """\
-----BEGIN CERTIFICATE-----
MIICxjCCAa6gAwIBAgIBATANBgkqhkiG9w0BAQsFADAcMRowGAYDVQQDDBF0dWd0
YWluZXItdGVzdC1jYTAeFw0yNjA4MjgxMzQ4MDJaFw0zNjA4MjUxMzQ4MDJaMBwx
GjAYBgNVBAMMEXR1Z3RhaW5lci10ZXN0LWNhMIIBIjANBgkqhkiG9w0BAQEFAAOC
AQ8AMIIBCgKCAQEAnGejUxabciz49R+hWfJEOkabZwRWP+wxT0uTX9S1lcXqIel9
qhA+DQkHeaChLLxqD6GB6sB80vQq2CVAbkK12NtcT5IDjuaqfIncBqIJWiXoM6YC
odv+UwGlYK/K/Bmbj0BE8IhaynGKAhMbcW/EeZF7mqZ/aU49pA71/OHdr1ggm8XE
WgEN6Xqxr4uo0UbZepFTTr5mDkGWCYVsobLGODe2O5by6wX0gQKfcsQvHSQaOKPo
bLiCyp67BP9x25FwoZQddW2YtSsmudiuWQin8BxGoTi819Nl0cc2ooClcJzpT+GD
eN/RPKWsaWvZoUbI9GIWzLTQJ+qZ+Qpxwu0CzwIDAQABoxMwETAPBgNVHRMBAf8E
BTADAQH/MA0GCSqGSIb3DQEBCwUAA4IBAQAvBy0EJl/Us+gbvLJ/O7TDVm9kGaH8
/WykSt01pvq71ZTUbI3KR6KGuqRcrkGJLJc3zzEHg08RAzgHcqpvq4HZWZcA0KU0
rcuDw8I4TrAeV5hdzbWmuuvBED+1zjvhOvOoEyHX6CsxZVYX4v0F/LeQpebxu/GK
vp3zWM1tJjODkFSugy9QFVm7Wy6f0HAYExcrv2NA2BO5yaq10RaHBOeZ09/ArLLV
x9OxkSp8QZ+h3oSliN8vUrrWu4Ov8Ha2OPD0KLisvNa4ek36bWRTjEzuyQs+QkH4
Qr+Hz+uRODZeAR08lqpOBzE9fYSFtVRQsangCdvvXhpb7mHpxKiPDOJc
-----END CERTIFICATE-----
""".strip()

_HOST_BODY = {
    "name": "remote",
    "enabled": True,
    "prune": False,
    "prune_all": False,
    "url": "https://agent.example.com",
    "ssl": True,
    "timeout": 5,
    "container_hc_timeout": 60,
}


def test_host_info_does_not_expose_secret():
    host = HostsModel(
        id=1,
        name="remote",
        enabled=True,
        prune=False,
        prune_all=False,
        url="https://agent.example.com",
        secret="sensitive",
        ssl=True,
        timeout=5,
        container_hc_timeout=60,
    )

    data = HostInfo.model_validate(host).model_dump()

    assert "secret" not in data
    assert data["has_secret"] is True
    assert data["ssl_ca"] is None


def test_host_info_reports_missing_secret():
    host = HostsModel(
        id=1,
        name="local",
        enabled=True,
        prune=False,
        prune_all=False,
        url="http://127.0.0.1:8001",
        secret="",
        ssl=True,
        timeout=5,
        container_hc_timeout=60,
    )

    data = HostInfo.model_validate(host).model_dump()

    assert data["has_secret"] is False


def test_host_info_exposes_ssl_ca():
    host = HostsModel(
        id=1,
        name="remote",
        enabled=True,
        prune=False,
        prune_all=False,
        url="https://agent.example.com",
        ssl=True,
        ssl_ca=TEST_CA_PEM,
        timeout=5,
        container_hc_timeout=60,
    )

    data = HostInfo.model_validate(host).model_dump()

    assert data["ssl_ca"] == TEST_CA_PEM


def test_host_create_accepts_valid_ssl_ca():
    body = HostCreate.model_validate({**_HOST_BODY, "ssl_ca": TEST_CA_PEM})
    assert body.ssl_ca == TEST_CA_PEM


def test_host_create_normalizes_blank_ssl_ca():
    assert HostCreate.model_validate({**_HOST_BODY, "ssl_ca": ""}).ssl_ca is None
    assert HostCreate.model_validate({**_HOST_BODY, "ssl_ca": "  \n"}).ssl_ca is None
    assert HostCreate.model_validate({**_HOST_BODY, "ssl_ca": None}).ssl_ca is None


def test_host_create_rejects_invalid_ssl_ca():
    with pytest.raises(ValidationError, match="Invalid CA certificate PEM"):
        HostCreate.model_validate({**_HOST_BODY, "ssl_ca": "not-a-cert"})


def test_host_update_accepts_and_clears_ssl_ca():
    body = HostUpdate.model_validate({**_HOST_BODY, "ssl_ca": TEST_CA_PEM})
    assert body.ssl_ca == TEST_CA_PEM
    assert HostUpdate.model_validate({**_HOST_BODY, "ssl_ca": ""}).ssl_ca is None
