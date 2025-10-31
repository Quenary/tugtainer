from python_on_whales.components.image.models import (
    ImageInspectResult,
)
from backend.schemas import ImageGetResponseBody
from backend.helpers.now import now


def map_image_schema(
    image: ImageInspectResult, dangling: bool, unused: bool
) -> ImageGetResponseBody:
    repodigests: list[str] = image.repo_digests or []
    repository = repodigests[0].split("@")[0] if repodigests else ""
    _image = ImageGetResponseBody(
        repository=repository,
        id=image.id or "",
        dangling=dangling,
        unused=unused,
        tags=image.repo_tags or [],
        size=image.size or 0,
        created=image.created or now(),
    )
    return _image
