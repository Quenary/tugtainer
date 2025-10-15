from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth_core import is_authorized
from app.schemas import ImageGetResponseBody
from app.api.util import map_image_schema, get_host
from python_on_whales import Container
from app.core import HostsManager
from app.db import get_async_session

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
    containers: list[Container] = client.container.list(all=True)
    used_images: list[str] = [c.image for c in containers]
    dangling_images: list[str] = [
        str(i.id)
        for i in client.image.list(filters=[("dangling", "true")])
    ]
    res: list[ImageGetResponseBody] = []
    for image in client.image.list(all=True):
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
    return client.image.prune()
