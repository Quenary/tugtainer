import docker
from docker.models.containers import Container
from fastapi import APIRouter, Depends
from app.core.auth_core import is_authorized
from app.schemas import ImageGetResponseBody, ImagePruneResponseBody
from app.api.util import map_image_schema

_client = docker.from_env()
router = APIRouter(
    prefix="/images",
    tags=["images"],
    dependencies=[Depends(is_authorized)],
)


@router.get(path="/list", response_model=list[ImageGetResponseBody])
def get_list() -> list[ImageGetResponseBody]:
    containers: list[Container] = _client.containers.list(all=True)
    used_images: list[str] = [c.attrs["Image"] for c in containers]
    dangling_images: list[str] = [
        str(i.id)
        for i in _client.images.list(filters={"dangling": True})
    ]
    res: list[ImageGetResponseBody] = []
    for image in _client.images.list():
        dangling = image.id in dangling_images
        unused = image.id not in used_images
        res.append(map_image_schema(image, dangling, unused))
    return res


@router.post(path="/prune", response_model=ImagePruneResponseBody)
def prune() -> ImagePruneResponseBody:
    return _client.images.prune()
