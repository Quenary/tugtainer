from typing import Any, Iterable, Mapping, Optional
from pydantic import BaseModel
from python_on_whales.components.image.cli_wrapper import (
    ImageListFilter,
)


class InspectImageRequestBodySchema(BaseModel):
    spec_or_id: str


class GetImageListBodySchema(BaseModel):
    repository_or_tag: Optional[str] = None
    filters: Optional[dict[str, Any]] = {}
    all: Optional[bool] = True


class PruneImagesRequestBodySchema(BaseModel):
    all: Optional[bool] = False
    filters: Optional[dict[str, Any]] = {}


class PullImageRequestBodySchema(BaseModel):
    image: str


class TagImageRequestBodySchema(BaseModel):
    spec_or_id: str
    tag: str
