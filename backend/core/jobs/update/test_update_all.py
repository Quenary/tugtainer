from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from backend.core.jobs.update.update_all import update_all_hosts

base_module = "backend.core.jobs.update.update_all"


@pytest.fixture
def mock_hosts(mocker: MockerFixture):
    host1 = SimpleNamespace(id=1, name="host1")
    host2 = SimpleNamespace(id=2, name="host2")

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [host1, host2]

    session = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)

    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    mocker.patch(f"{base_module}.async_session_maker", return_value=session_cm)

    mocker.patch(
        f"{base_module}.job_to_notification_result",
        side_effect=lambda j: j,
    )
    mocker.patch(f"{base_module}.send_job_notification", AsyncMock())

    return [host1, host2]


@pytest.mark.asyncio
async def test_update_all_hosts_default_scheduled(
    mocker: MockerFixture, mock_hosts: list[SimpleNamespace]
):
    mock_submit = mocker.patch(
        f"{base_module}.host_job_coordinator.submit",
        AsyncMock(return_value=SimpleNamespace(job={"kind": "update", "names": None})),
    )

    await update_all_hosts()

    assert mock_submit.call_count == 2
    for host in mock_hosts:
        mock_submit.assert_any_call(
            host,
            "update",
            names=None,
            manual=False,
            wait=True,
        )


@pytest.mark.asyncio
async def test_update_all_hosts_manual(
    mocker: MockerFixture, mock_hosts: list[SimpleNamespace]
):
    mock_submit = mocker.patch(
        f"{base_module}.host_job_coordinator.submit",
        AsyncMock(return_value=SimpleNamespace(job={"kind": "update", "names": None})),
    )

    await update_all_hosts(manual=True)

    assert mock_submit.call_count == 2
    for host in mock_hosts:
        mock_submit.assert_any_call(
            host,
            "update",
            names=None,
            manual=True,
            wait=True,
        )


@pytest.mark.asyncio
async def test_update_all_hosts_handles_host_failure(
    mocker: MockerFixture, mock_hosts: list[SimpleNamespace]
):
    async def fake_submit(host, *args, **kwargs):
        if host.id == 1:
            raise RuntimeError("Agent down")
        return SimpleNamespace(job={"kind": "update", "names": None})

    mocker.patch(
        f"{base_module}.host_job_coordinator.submit",
        side_effect=fake_submit,
    )
    mock_notify = mocker.patch(
        f"{base_module}.send_job_notification",
        AsyncMock(),
    )

    # Should not raise exception
    await update_all_hosts(manual=True)

    assert mock_notify.call_count == 1
    call_args = mock_notify.call_args[0][0]
    assert len(call_args) == 1
