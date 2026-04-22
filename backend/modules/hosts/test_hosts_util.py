import pytest
from pytest_mock import MockerFixture
from unittest.mock import MagicMock

from backend.modules.hosts.hosts_util import (
    annotate_available_updates_count,
)


@pytest.mark.asyncio
async def test_annotate_noop_on_empty_list(mocker: MockerFixture):
    session = mocker.AsyncMock()
    session.execute = mocker.AsyncMock()

    await annotate_available_updates_count([], session)

    session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_annotate_zero_when_query_returns_nothing(
    mocker: MockerFixture,
):
    host = MagicMock()
    host.id = 1

    result = MagicMock()
    result.all.return_value = []
    session = mocker.AsyncMock()
    session.execute = mocker.AsyncMock(return_value=result)

    await annotate_available_updates_count([host], session)

    assert host.available_updates_count == 0


@pytest.mark.asyncio
async def test_annotate_populates_counts_and_defaults_missing(
    mocker: MockerFixture,
):
    host_a, host_b, host_c = MagicMock(), MagicMock(), MagicMock()
    host_a.id, host_b.id, host_c.id = 1, 2, 3

    result = MagicMock()
    # host_c is intentionally absent from the query result; its count must
    # fall back to 0.
    result.all.return_value = [(1, 3), (2, 1)]
    session = mocker.AsyncMock()
    session.execute = mocker.AsyncMock(return_value=result)

    await annotate_available_updates_count(
        [host_a, host_b, host_c], session
    )

    assert host_a.available_updates_count == 3
    assert host_b.available_updates_count == 1
    assert host_c.available_updates_count == 0
