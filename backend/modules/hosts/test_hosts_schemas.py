from backend.modules.hosts.hosts_model import HostsModel
from backend.modules.hosts.hosts_schemas import HostInfo


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
