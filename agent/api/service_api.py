import json
import logging
from typing import Final, cast

from fastapi import APIRouter, Depends, HTTPException, status
from python_on_whales.utils import run

from agent.auth import verify_signature
from agent.docker_client import DOCKER
from agent.unil.asyncall import asyncall
from shared.schemas.service_schemas import (
    ServiceListItemSchema,
    ServiceReplicasSchema,
    ServiceUpdateRequestBody,
)

logger: Final = logging.getLogger(__name__)

router = APIRouter(
    prefix="/service",
    tags=["service"],
    dependencies=[Depends(verify_signature)],
)


def _check_swarm_manager() -> None:
    info = DOCKER.info()
    if not (info.swarm and info.swarm.control_available):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Docker is not in swarm manager mode",
        )


@router.get(
    "/list",
    description="Get list of all swarm services with replica counts",
    response_model=list[ServiceListItemSchema],
)
async def list_services() -> list[ServiceListItemSchema]:
    def _get_services() -> list[ServiceListItemSchema]:
        _check_swarm_manager()
        services = DOCKER.service.list()
        if not services:
            return []

        ids = [s.id for s in services]
        raw_output = cast(str, run(DOCKER.docker_cmd + ["service", "inspect"] + ids))
        raw_list: list[dict] = json.loads(raw_output)

        replica_map: dict[str, tuple[int, int | None]] = {}
        try:
            ls_output = cast(
                str,
                run(DOCKER.docker_cmd + ["service", "ls", "--format", "{{json .}}"]),
            )
            for line in ls_output.strip().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    rep_str = data.get("Replicas", "")
                    if "/" in rep_str:
                        parts = rep_str.split("/")
                        running = int(parts[0]) if parts[0].isdigit() else 0
                        desired = (
                            int(parts[1])
                            if len(parts) > 1 and parts[1].isdigit()
                            else None
                        )
                        if data.get("Name"):
                            replica_map[data["Name"]] = (running, desired)
                        if data.get("ID"):
                            replica_map[data["ID"]] = (running, desired)
                except Exception as e:
                    logger.debug(f"Failed to parse service ls line: {e}")
        except Exception as e:
            logger.warning(f"Failed to run docker service ls: {e}")

        items: list[ServiceListItemSchema] = []
        for svc in raw_list:
            spec = svc.get("Spec") or {}
            task_template = spec.get("TaskTemplate") or {}
            container_spec = task_template.get("ContainerSpec") or {}
            mode_dict = spec.get("Mode") or {}
            mode = "global" if "Global" in mode_dict else "replicated"

            svc_id = svc.get("ID", "")
            svc_name = spec.get("Name", "")

            if svc_name in replica_map:
                running_tasks, desired_tasks = replica_map[svc_name]
            elif svc_id in replica_map:
                running_tasks, desired_tasks = replica_map[svc_id]
            else:
                service_status = svc.get("ServiceStatus") or {}
                running_tasks = service_status.get("RunningTasks", 0)
                desired_tasks = service_status.get("DesiredTasks")
                if desired_tasks is None and mode == "replicated":
                    desired_tasks = mode_dict.get("Replicated", {}).get("Replicas", 1)

            update_status = svc.get("UpdateStatus") or {}

            items.append(
                ServiceListItemSchema(
                    id=svc.get("ID", ""),
                    name=spec.get("Name", ""),
                    image=container_spec.get("Image", ""),
                    mode=mode,
                    replicas=ServiceReplicasSchema(
                        running=running_tasks,
                        desired=desired_tasks,
                    ),
                    labels=spec.get("Labels") or {},
                    update_status_state=update_status.get("State"),
                    update_status_message=update_status.get("Message"),
                    created_at=svc.get("CreatedAt"),
                    updated_at=svc.get("UpdatedAt"),
                )
            )
        return items

    return await asyncall(_get_services)


@router.get(
    "/inspect/{name_or_id}",
    description="Inspect a swarm service",
)
async def inspect_service(name_or_id: str) -> dict:
    def _do_inspect() -> dict:
        _check_swarm_manager()
        raw_output = cast(
            str, run(DOCKER.docker_cmd + ["service", "inspect", name_or_id])
        )
        raw = json.loads(raw_output)
        if not raw:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                f"Service {name_or_id} not found",
            )
        return raw[0]

    return await asyncall(_do_inspect)


@router.post(
    "/update",
    description="Update a swarm service to a new image (detached rolling update)",
    response_model=str,
)
async def update_service(body: ServiceUpdateRequestBody) -> str:
    def _do_update() -> str:
        _check_swarm_manager()
        DOCKER.service.update(
            body.service_id,
            image=body.image,
            detach=True,
            with_registry_authentication=True,
        )
        return body.service_id

    return await asyncall(_do_update, asyncall_timeout=60)


@router.get(
    "/logs/{name_or_id}",
    description="Get aggregated logs for a swarm service",
    response_model=str,
)
async def service_logs(
    name_or_id: str,
    tail: int = 100,
    timestamps: bool = False,
) -> str:
    def _do_logs() -> str:
        _check_swarm_manager()
        result = DOCKER.service.logs(name_or_id, tail=tail, timestamps=timestamps)
        return str(result) if result else ""

    return await asyncall(_do_logs, asyncall_timeout=60)
