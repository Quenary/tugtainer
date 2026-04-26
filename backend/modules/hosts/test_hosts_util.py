from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

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
@pytest.mark.parametrize(
    "host_ids, db_rows, expected",
    [
        # базовый кейс (твой текущий)
        ([1, 2, 3], [(1, 3), (2, 1)], {1: 3, 2: 1, 3: 0}),
        # все хосты есть
        ([1, 2], [(1, 5), (2, 7)], {1: 5, 2: 7}),
        # никто не вернулся из БД
        ([1, 2], [], {1: 0, 2: 0}),
        # один хост
        ([42], [(42, 9)], {42: 9}),
        # пустой список (важный edge case)
        ([], [], {}),
    ],
)
async def test_annotate_available_updates_count(
    mocker,
    host_ids,
    db_rows,
    expected,
):
    hosts = []
    for hid in host_ids:
        h = MagicMock()
        h.id = hid
        hosts.append(h)

    result = MagicMock()
    result.all.return_value = db_rows

    session = mocker.AsyncMock()
    session.execute = mocker.AsyncMock(return_value=result)

    await annotate_available_updates_count(hosts, session)

    for h in hosts:
        assert h.available_updates_count == expected[h.id]

    # дополнительная проверка: если список пустой — execute не вызывается
    if not hosts:
        session.execute.assert_not_called()
    else:
        session.execute.assert_called_once()
