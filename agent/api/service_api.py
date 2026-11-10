import logging
from typing import Any, Final

from fastapi import APIRouter, Depends, HTTPException, status

from agent.auth import verify_signature
from agent.docker_client import RUNTIME_CLIENT
from shared.runtime.registry_auth import registry_auth_for_image
from shared.schemas.service_schemas import (
    ServiceListItemSchema,
    ServiceReplicasSchema,
    ServiceUpdateRequestBody,
    ServiceUpdateResponse,
)

logger: Final = logging.getLogger(__name__)

router = APIRouter(
    prefix="/service",
    tags=["service"],
    dependencies=[Depends(verify_signature)],
)


async def _check_swarm_manager() -> None:
    info = await RUNTIME_CLIENT.get_info()
    swarm = info.get("Swarm") or {}
    control = swarm.get("ControlAvailable") or swarm.get("control_available")
    if not (swarm and control):
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
    await _check_swarm_manager()
    raw_list = await RUNTIME_CLIENT.service_list()
    items: list[ServiceListItemSchema] = []
    for svc in raw_list:
        spec = svc.get("Spec") or {}
        task_template = spec.get("TaskTemplate") or {}
        container_spec = task_template.get("ContainerSpec") or {}
        mode_dict = spec.get("Mode") or {}
        mode = "global" if "Global" in mode_dict else "replicated"

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


@router.get(
    "/inspect/{name_or_id}",
    description="Inspect a swarm service",
)
async def inspect_service(name_or_id: str) -> dict[str, Any]:
    await _check_swarm_manager()
    res = await RUNTIME_CLIENT.service_inspect(name_or_id)
    if not res:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Service {name_or_id} not found",
        )
    return res


@router.post(
    "/update",
    description="Update a swarm service to a new image (detached rolling update)",
    response_model=ServiceUpdateResponse,
)
async def update_service(body: ServiceUpdateRequestBody) -> ServiceUpdateResponse:
    await _check_swarm_manager()
    applied = await RUNTIME_CLIENT.service_update(
        body.service_id,
        body.image,
        auth_config=registry_auth_for_image(body.image),
    )
    return ServiceUpdateResponse(service_id=body.service_id, applied=applied)


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
    await _check_swarm_manager()
    return await RUNTIME_CLIENT.service_logs(
        name_or_id, tail=tail, timestamps=timestamps
    )
