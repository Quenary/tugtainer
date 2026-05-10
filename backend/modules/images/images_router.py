from typing import Final

from fastapi import APIRouter, Depends
from python_on_whales.components.image.models import ImageInspectResult
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.agent_client import AgentClientManager
from backend.db.session import get_async_session
from backend.modules.auth.auth_util import is_authorized
from backend.modules.hosts.hosts_util import get_host
from backend.modules.images.images_util import map_image_schema
from shared.schemas.container_schemas import (
    GetContainerListBodySchema,
)
from shared.schemas.image_schemas import (
    GetImageListBodySchema,
    InspectImageRequestBodySchema,
    PruneImagesRequestBodySchema,
)

from .images_schemas import ImageGetResponseBody

images_router = APIRouter(
    prefix="/images",
    tags=["images"],
    dependencies=[Depends(is_authorized)],
)


@images_router.get(path="/{host_id}/list", response_model=list[ImageGetResponseBody])
async def get_list(
    host_id: int, session: AsyncSession = Depends(get_async_session)
) -> list[ImageGetResponseBody]:
    host: Final = await get_host(host_id, session)
    client: Final = AgentClientManager.get_host_client(host)

    containers: Final = await client.container.list(
        GetContainerListBodySchema(all=True)
    )
    used_images: Final[set[str]] = {c.image for c in containers if c.image}
    images: Final = await client.image.list(GetImageListBodySchema(all=True))

    return [
        map_image_schema(
            image,
            dangling=bool(not image.repo_tags and image.id not in used_images),
            unused=bool(image.id not in used_images),
        )
        for image in images
    ]


@images_router.get(
    path="/{host_id}/{image_spec_or_id}",
    description="Get image info (inspect)",
    response_model=ImageInspectResult,
)
async def inspect(
    host_id: int,
    image_spec_or_id: str,
    session: AsyncSession = Depends(get_async_session),
) -> ImageInspectResult:
    host: Final = await get_host(host_id, session)
    client: Final = AgentClientManager.get_host_client(host)
    return await client.image.inspect(
        InspectImageRequestBodySchema(spec_or_id=image_spec_or_id)
    )


@images_router.post(path="/{host_id}/prune", response_model=str)
async def prune(
    host_id: int,
    body: PruneImagesRequestBodySchema,
    session: AsyncSession = Depends(get_async_session),
) -> str:
    host = await get_host(host_id, session)
    client = AgentClientManager.get_host_client(host)
    return await client.image.prune(body)
