from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel


class ContainerGetResponseBody(BaseModel):
    name: str
    image: str
    short_id: str
    ports: dict[str, Any]
    status: str
    health: str
    is_self: bool
    # Those keys stored in db, but might be undefined for new containers
    check_enabled: Optional[bool] = None  # Is check for update enabled
    update_enabled: Optional[bool] = None  # Is auto update enabled
    update_available: Optional[bool] = None  # Is container update available
    checked_at: Optional[datetime] = None  # Date of check for update
    updated_at: Optional[datetime] = None  # Date of last update
    created_at: Optional[datetime] = None  # Date of creation of db entry
    modified_at: Optional[datetime] = None  # Date ofmodification db entry


class ContainerPatchRequestBody(BaseModel):
    check_enabled: Optional[bool] = None
    update_enabled: Optional[bool] = None
