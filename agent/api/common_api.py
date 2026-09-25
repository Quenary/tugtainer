from fastapi import APIRouter, Depends

from agent.auth import verify_signature
from agent.docker_client import DOCKER
from agent.unil.asyncall import asyncall
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
async def get_version():
    return await asyncall(lambda: DOCKER.version())


@router.get(
    "/swarm-info",
    description="Get docker swarm info",
    response_model=SwarmInfoSchema,
)
async def get_swarm_info() -> SwarmInfoSchema:
    def _fetch_swarm_info() -> SwarmInfoSchema:
        info = DOCKER.info()
        swarm = info.swarm
        if swarm and swarm.local_node_state == "active":
            cluster_id = swarm.cluster.id if swarm.cluster else None
            return SwarmInfoSchema(
                cluster_id=cluster_id or None,
                node_id=swarm.node_id or None,
                is_manager=bool(swarm.control_available),
            )
        return SwarmInfoSchema(
            cluster_id=None,
            node_id=None,
            is_manager=False,
        )

    return await asyncall(_fetch_swarm_info)
