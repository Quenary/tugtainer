from datetime import datetime
from typing import cast
from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from backend.modules.containers.containers_model import (
    ContainersModel,
)


def filter_containers_by_check_enabled(
    containers: list[ContainerInspectResult],
    containers_db_map: dict[str, ContainersModel],
    manual: bool = False,
) -> list[ContainerInspectResult]:
    if manual:
        return containers
    _containers: list[ContainerInspectResult] = []
    for c in containers:
        c_db = containers_db_map.get(cast(str, c.name))
        if c_db and c_db.check_enabled:
            _containers.append(c)
    return _containers


def sort_containers_by_checked_at(
    containers: list[ContainerInspectResult],
    containers_db_map: dict[str, ContainersModel],
) -> list[ContainerInspectResult]:
    """
    Sort containers by checked_at date
    (from earliest to latest)
    """
    return sorted(
        containers,
        key=lambda c: (
            (c_db := containers_db_map.get(cast(str, c.name)))
            is not None
            and c_db.checked_at is not None,
            (
                c_db.checked_at
                if c_db and c_db.checked_at
                else datetime.min
            ),
        ),
    )
