from app.schemas import ImageGetResponseBody
from python_on_whales import Image


def map_image_schema(
    image: Image, dangling: bool, unused: bool
) -> ImageGetResponseBody:
    repodigests: list[str] = image.repo_digests
    repository = repodigests[0].split("@")[0] if repodigests else ""
    size = image.size
    _image = ImageGetResponseBody(
        repository=repository,
        id=image.id,
        dangling=dangling,
        unused=unused,
        tags=image.repo_tags,
        size=image.size,
        created=image.created,
    )
    return _image
