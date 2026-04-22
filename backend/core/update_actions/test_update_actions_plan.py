import pytest
from unittest.mock import AsyncMock
from typing import Any, Sequence, cast
from backend.core.update_actions.update_actions_plan import (
    build_update_plan,
)

# Предполагаем, что функция импортирована
# from your_module import build_update_plan


base_module = "backend.core.update_actions.update_actions_plan"


class DummyContainer:
    def __init__(self, name, labels=None):
        self.name = name
        self.labels = labels or {}


class DummyDB:
    def __init__(
        self, name, update_available=True, update_enabled=True
    ):
        self.name = name
        self.update_available = update_available
        self.update_enabled = update_enabled


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "containers, db_items, deps, manual_for, expected",
    [
        # Простая цепочка DB -> API -> FE (обновляем API)
        (
            ["db", "api", "fe"],
            {
                "db": DummyDB("db", False),
                "api": DummyDB("api", True),
                "fe": DummyDB("fe", False),
            },
            {
                "api": {"db"},
                "fe": {"api"},
                "db": set(),
            },
            [],
            {
                "to_update": {"api"},
                "affected": {"fe"},
                "order": ["db", "api", "fe"],
            },
        ),
        # Пересечение зависимостей (API + Worker)
        (
            ["db", "api", "worker", "fe"],
            {
                "db": DummyDB("db", False),
                "api": DummyDB("api", True),
                "worker": DummyDB("worker", True),
                "fe": DummyDB("fe", False),
            },
            {
                "api": {"db"},
                "worker": {"db"},
                "fe": {"api", "worker"},
                "db": set(),
            },
            [],
            {
                "to_update": {"api", "worker"},
                "affected": {"fe"},
                "order": ["db", "api", "worker", "fe"],
            },
        ),
        # Manual override
        (
            ["db", "api"],
            {
                "db": DummyDB("db", True),
                "api": DummyDB("api", True),
            },
            {
                "api": {"db"},
                "db": set(),
            },
            ["db"],
            {
                "to_update": {"db"},
                "affected": {"api"},
                "order": ["db", "api"],
            },
        ),
        # Большой single-compose (2 цепочки + одиночные)
        (
            [
                "db1",
                "api1",
                "fe1",  # цепочка 1
                "db2",
                "api2",
                "worker2",  # цепочка 2
                "redis",
                "nginx",
                "cron",
                "metrics",  # одиночные
            ],
            {
                "db1": DummyDB("db1", False),
                "api1": DummyDB("api1", True),  # обновляется
                "fe1": DummyDB("fe1", False),
                "db2": DummyDB("db2", False),
                "api2": DummyDB("api2", True),  # обновляется
                "worker2": DummyDB("worker2", False),
                "redis": DummyDB("redis", False),
                "nginx": DummyDB("nginx", False),
                "cron": DummyDB("cron", False),
                "metrics": DummyDB("metrics", False),
            },
            {
                # цепочка 1
                "api1": {"db1"},
                "fe1": {"api1"},
                # цепочка 2
                "api2": {"db2"},
                "worker2": {"api2"},
                # одиночные
                "db1": set(),
                "db2": set(),
                "redis": set(),
                "nginx": set(),
                "cron": set(),
                "metrics": set(),
            },
            [],
            {
                "to_update": {"api1", "api2"},
                "affected": {"fe1", "worker2"},
                # order — set, поэтому просто все задействованные + их deps
                "order": [
                    "db1",
                    "api1",
                    "fe1",
                    "db2",
                    "api2",
                    "worker2",
                ],
            },
        ),
    ],
)
async def test_build_update_plan(
    mocker,
    containers: Sequence[str],
    db_items,
    deps,
    manual_for,
    expected,
):
    # --- Containers
    container_objs = [DummyContainer(name=c) for c in containers]

    # --- DB mock
    db_list = list(db_items.values())

    mock_result = mocker.Mock()
    mock_result.scalars.return_value.all.return_value = db_list

    async_session_mock = AsyncMock()
    async_session_mock.execute.return_value = mock_result

    async def session_ctx(*args, **kwargs):
        return async_session_mock

    async_session_ctx_mock = AsyncMock()
    async_session_ctx_mock.__aenter__ = session_ctx

    # мок async_session_maker()
    mocker.patch(
        f"{base_module}.async_session_maker",
        return_value=async_session_ctx_mock,
    )

    # --- Settings
    mocker.patch(
        f"{base_module}.SettingsStorage.get",
        return_value=False,  # UPDATE_ONLY_RUNNING = False
    )

    # --- Helpers
    mocker.patch(
        f"{base_module}.is_protected_container",
        return_value=False,
    )

    mocker.patch(
        f"{base_module}.is_running_container",
        return_value=True,
    )

    mocker.patch(
        f"{base_module}.get_service_name",
        return_value=None,
    )

    mocker.patch(
        f"{base_module}.get_compose_id",
        return_value=None,
    )

    def get_deps(container, _label):
        return deps.get(container.name, set())

    mocker.patch(
        f"{base_module}.get_dependencies",
        side_effect=get_deps,
    )

    # --- manual_for objects
    manual_objs = [DummyContainer(name=c) for c in manual_for]

    # --- Host
    host = mocker.Mock()
    host.id = 1

    # --- Run
    plan = await build_update_plan(
        host,
        cast(Any, container_objs),
        cast(Any, manual_objs),
    )

    def assert_topo_order(order, deps):
        pos = {name: i for i, name in enumerate(order)}
        for node, node_deps in deps.items():
            for dep in node_deps:
                assert pos[dep] < pos[node], f"{dep} should be before {node}"

    # --- Assert
    assert plan.to_update == expected["to_update"]
    assert plan.affected == expected["affected"]
    assert sorted(plan.order) == sorted(expected["order"])
    assert_topo_order(plan.order, deps)
