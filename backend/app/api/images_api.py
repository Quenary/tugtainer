from fastapi import APIRouter, Depends
from app.core.auth_core import is_authorized
from app.schemas import ImageGetResponseBody, ImagePruneResponseBody
from app.api.util import map_image_schema
from python_on_whales import docker, Container, Image

router = APIRouter(
    prefix="/images",
    tags=["images"],
    dependencies=[Depends(is_authorized)],
)


@router.get(path="/list", response_model=list[ImageGetResponseBody])
def get_list() -> list[ImageGetResponseBody]:
    containers: list[Container] = docker.container.list(all=True)
    used_images: list[str] = [c.image for c in containers]
    dangling_images: list[str] = [
        str(i.id)
        for i in docker.image.list(filters=[("dangling","true")])
    ]
    res: list[ImageGetResponseBody] = []
    for image in docker.image.list(all=True):
        dangling = image.id in dangling_images
        unused = image.id not in used_images
        res.append(map_image_schema(image, dangling, unused))
    return res


@router.post(path="/prune", response_model=str)
def prune() -> str:
    return docker.image.prune()
