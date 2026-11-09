from fastapi import APIRouter, Depends

from agent.auth import verify_signature
from agent.docker_client import RUNTIME_CLIENT
from shared.schemas.docker_version_scheme import DockerVersionScheme
from shared.schemas.service_schemas import SwarmInfoSchema

router = APIRouter(
    prefix="/common",
    tags=["common"],
    dependencies=[Depends(verify_signature)],
)


@router.get(
    "/version",
    description="Get docker version",
    response_model=DockerVersionScheme,
)
async def get_version() -> DockerVersionScheme:
    return await RUNTIME_CLIENT.get_version()


@router.get(
    "/swarm-info",
    description="Get docker swarm info",
    response_model=SwarmInfoSchema,
)
async def get_swarm_info() -> SwarmInfoSchema:
    info = await RUNTIME_CLIENT.get_info()
    swarm = info.get("Swarm") or {}
    local_state = swarm.get("LocalNodeState") or swarm.get("local_node_state")
    if local_state == "active":
        cluster = swarm.get("Cluster") or {}
        cluster_id = cluster.get("ID") or cluster.get("id")
        node_id = swarm.get("NodeID") or swarm.get("node_id")
        control = swarm.get("ControlAvailable") or swarm.get("control_available")
        return SwarmInfoSchema(
            cluster_id=cluster_id or None,
            node_id=node_id or None,
            is_manager=bool(control),
        )
    return SwarmInfoSchema(
        cluster_id=None,
        node_id=None,
        is_manager=False,
    )
