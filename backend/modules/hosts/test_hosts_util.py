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


@pytest.mark.asyncio
async def test_annotate_available_updates_count_with_swarm_hosts(mocker: MockerFixture):
    h1 = MagicMock()
    h1.id = 1
    h1.is_swarm = False

    h2 = MagicMock()
    h2.id = 2
    h2.is_swarm = True

    hosts = [h1, h2]

    # First execute: container updates (host 1 has 2, host 2 has 1)
    container_result = MagicMock()
    container_result.all.return_value = [(1, 2), (2, 1)]

    # Second execute: swarm service updates (host 2 has 3 service updates)
    service_result = MagicMock()
    service_result.all.return_value = [(2, 3)]

    session = mocker.AsyncMock()
    session.execute = mocker.AsyncMock(side_effect=[container_result, service_result])

    await annotate_available_updates_count(hosts, session)  # type: ignore[arg-type]

    assert h1.available_updates_count == 2
    assert h2.available_updates_count == 4  # 1 container + 3 services
    assert session.execute.call_count == 2


@pytest.mark.asyncio
async def test_annotate_available_updates_count_swarm_only_services(
    mocker: MockerFixture,
):
    h = MagicMock()
    h.id = 5
    h.is_swarm = True

    container_result = MagicMock()
    container_result.all.return_value = []  # 0 container updates

    service_result = MagicMock()
    service_result.all.return_value = [(5, 4)]  # 4 service updates

    session = mocker.AsyncMock()
    session.execute = mocker.AsyncMock(side_effect=[container_result, service_result])

    await annotate_available_updates_count([h], session)  # type: ignore[arg-type]

    assert h.available_updates_count == 4
    assert session.execute.call_count == 2
