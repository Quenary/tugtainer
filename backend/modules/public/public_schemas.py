
from pydantic import BaseModel, ConfigDict


class IsUpdateAvailableResponseBodySchema(BaseModel):
    is_available: bool
    release_url: str

    model_config = ConfigDict(from_attributes=True)




class TotalUpdateCountResponseBodySchema(BaseModel):
    total_updates: int


class VersionResponseBody(BaseModel):
    """Versions schema"""

    image_version: str | None = None
