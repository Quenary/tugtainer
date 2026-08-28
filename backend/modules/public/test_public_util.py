import pytest
from pytest_mock import MockerFixture
from python_on_whales.components.container.models import (
    ContainerInspectResult,
)

from backend.modules.containers.containers_model import ContainersModel
from backend.modules.hosts.hosts_model import HostsModel
from backend.modules.public.public_util import get_host_summary

module_path = "backend.modules.public.public_util"


def _host(*, enabled: bool = True) -> HostsModel:
    return HostsModel(
        id=1,
        name="host1",
        enabled=enabled,
        url="http://example",
        secret=None,
        ssl=True,
        timeout=5,
        container_hc_timeout=60,
        prune=False,
        prune_all=False,
    )


def _container_db(
    name: str,
    *,
    check_enabled: bool,
    update_available: bool,
) -> ContainersModel:
    return ContainersModel(
        host_id=1,
        name=name,
        check_enabled=check_enabled,
        update_enabled=False,
        update_available=update_available,
        image_id=None,
    )


@pytest.mark.asyncio
async def test_get_host_summary_disabled_host_zeros_auto_check():
    summary = await get_host_summary(_host(enabled=False), session=None)

    assert summary.host_enabled is False
    assert summary.by_update_available == {"true": 0, "false": 0}
    assert summary.by_update_available_auto_check == {"true": 0, "false": 0}


@pytest.mark.asyncio
async def test_get_host_summary_auto_check_counts_only_check_enabled(
    mocker: MockerFixture,
):
    fake_client = mocker.Mock()
    fake_client.container.list = mocker.AsyncMock(
        return_value=[
            ContainerInspectResult(id="1", name="checked-available"),
            ContainerInspectResult(id="2", name="checked-current"),
            ContainerInspectResult(id="3", name="unchecked-available"),
        ]
    )
    fake_client.image.list = mocker.AsyncMock(return_value=[])
    mocker.patch(
        f"{module_path}.AgentClientManager.get_host_client",
        return_value=fake_client,
    )

    db_result = mocker.Mock()
    db_result.scalars.return_value.all.return_value = [
        _container_db("checked-available", check_enabled=True, update_available=True),
        _container_db("checked-current", check_enabled=True, update_available=False),
        _container_db(
            "unchecked-available", check_enabled=False, update_available=True
        ),
    ]
    session = mocker.AsyncMock()
    session.execute = mocker.AsyncMock(return_value=db_result)

    summary = await get_host_summary(_host(), session)

    assert summary.by_update_available == {"true": 2, "false": 1}
    assert summary.by_update_available_auto_check == {"true": 1, "false": 1}
