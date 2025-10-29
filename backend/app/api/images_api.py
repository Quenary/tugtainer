from fastapi import APIRouter, Depends
from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.auth_core import is_authorized
from backend.app.schemas import ImageGetResponseBody
from backend.app.api.util import map_image_schema, get_host
from backend.app.core import HostsManager
from backend.app.db.session import get_async_session
from shared.schemas.container_schemas import (
    GetContainerListBodySchema,
)
from shared.schemas.image_schemas import (
    GetImageListBodySchema,
    PruneImagesRequestBodySchema,
)

router = APIRouter(
    prefix="/images",
    tags=["images"],
    dependencies=[Depends(is_authorized)],
)


@router.get(
    path="/{host_id}/list", response_model=list[ImageGetResponseBody]
)
async def get_list(
    host_id: int, session: AsyncSession = Depends(get_async_session)
) -> list[ImageGetResponseBody]:
    host = await get_host(host_id, session)
    client = HostsManager.get_host_client(host)
    containers: list[ContainerInspectResult] = (
        await client.container.list(
            GetContainerListBodySchema(all=True)
        )
    )
    used_images: list[str] = [c.image for c in containers if c.image]
    dangling_images: list[str] = [
        str(i.id)
        for i in await client.image.list(
            GetImageListBodySchema(filters={"dangling": "true"})
        )
    ]
    res: list[ImageGetResponseBody] = []
    for image in await client.image.list(
        GetImageListBodySchema(all=True)
    ):
        dangling = image.id in dangling_images
        unused = image.id not in used_images
        res.append(map_image_schema(image, dangling, unused))
    return res


@router.post(path="/{host_id}/prune", response_model=str)
async def prune(
    host_id: int, session: AsyncSession = Depends(get_async_session)
) -> str:
    host = await get_host(host_id, session)
    client = HostsManager.get_host_client(host)
    return await client.image.prune(
        PruneImagesRequestBodySchema(all=True)
    )
