from docker.models.images import Image
from app.schemas import ImageGetResponseBody


def map_image_schema(
    image: Image, dangling: bool, unused: bool
) -> ImageGetResponseBody:
    repodigests: list[str] = image.attrs.get("RepoDigests", [])
    repository = repodigests[0].split("@")[0] if repodigests else ""
    size = image.attrs.get("Size", 0)
    created = image.attrs.get("Created", "")
    _image = ImageGetResponseBody(
        repository=repository,
        id=str(image.id),
        dangling=dangling,
        unused=unused,
        tags=image.tags,
        size=size,
        created=created,
    )
    return _image
