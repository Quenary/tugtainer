"""Importable helpers for agent tests.

Pytest discovers fixtures from ``conftest.py``. Factories that tests call
directly live here so modules do not import ``conftest``.
"""

from typing import Any, Literal
from unittest.mock import MagicMock


def make_swarm_info(
    *,
    control_available: bool = False,
    local_node_state: str = "inactive",
    node_id: str | None = None,
    cluster_id: str | None = None,
    with_cluster: bool = True,
) -> MagicMock:
    info = MagicMock()
    swarm = info.swarm
    swarm.local_node_state = local_node_state
    swarm.control_available = control_available
    swarm.node_id = node_id
    if with_cluster:
        swarm.cluster = MagicMock()
        swarm.cluster.id = cluster_id
    else:
        swarm.cluster = None
    return info


def make_service_inspect(
    service_id: str,
    name: str,
    image: str,
    *,
    mode: Literal["replicated", "global"] = "replicated",
    replicas: int | None = None,
    running_tasks: int | None = None,
    desired_tasks: int | None = None,
    labels: dict[str, str] | None = None,
    update_state: str | None = None,
    update_message: str | None = None,
) -> dict[str, Any]:
    if mode == "global":
        mode_dict: dict[str, Any] = {"Global": {}}
    else:
        mode_dict = {"Replicated": {"Replicas": 1 if replicas is None else replicas}}
    spec: dict[str, Any] = {
        "Name": name,
        "Mode": mode_dict,
        "TaskTemplate": {"ContainerSpec": {"Image": image}},
    }
    if labels is not None:
        spec["Labels"] = labels
    item: dict[str, Any] = {"ID": service_id, "Spec": spec}
    if running_tasks is not None or desired_tasks is not None:
        status: dict[str, Any] = {}
        if running_tasks is not None:
            status["RunningTasks"] = running_tasks
        if desired_tasks is not None:
            status["DesiredTasks"] = desired_tasks
        item["ServiceStatus"] = status
    if update_state is not None or update_message is not None:
        item["UpdateStatus"] = {"State": update_state, "Message": update_message}
    return item
