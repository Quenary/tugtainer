from datetime import datetime
from pydantic import BaseModel


class ImageGetResponseBody(BaseModel):
    repository: str
    id: str
    dangling: bool
    unused: bool
    tags: list[str]
    size: int
    created: datetime


class ImagePruneResponseBody(BaseModel):
    ImagesDeleted: list[dict] | None
    SpaceReclaimed: int
