from typing import Any

from pydantic import BaseModel


class InspectImageRequestBodySchema(BaseModel):
    spec_or_id: str


class GetImageListBodySchema(BaseModel):
    repository_or_tag: str | None = None
    filters: dict[str, Any] | None = {}
    all: bool | None = True


class PruneImagesRequestBodySchema(BaseModel):
    all: bool | None = False
    filters: dict[str, Any] | None = {}


class PullImageRequestBodySchema(BaseModel):
    image: str


class TagImageRequestBodySchema(BaseModel):
    spec_or_id: str
    tag: str
