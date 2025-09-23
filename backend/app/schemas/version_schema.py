from pydantic import BaseModel
from typing import Optional


class VersionResponseBody(BaseModel):
    """Versions schema"""

    image_version: Optional[str] = None
