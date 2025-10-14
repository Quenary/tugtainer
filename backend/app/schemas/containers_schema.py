from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from python_on_whales.components.container.models import PortBinding


class ContainerGetResponseBody(BaseModel):
    name: str  # name of the container
    container_id: str  # id of the container
    image: str | None  # image of the container
    ports: Dict[str, List[PortBinding] | None] | None
    status: str | None
    health: str | None
    is_self: bool
    host_id: int  # host id is also stored in db, but it must be always defined
    # Those keys stored in db, but might be undefined for new containers
    id: Optional[int] = None  # id of the row
    check_enabled: Optional[bool] = (
        None  # Is check for update enabled
    )
    update_enabled: Optional[bool] = None  # Is auto update enabled
    update_available: Optional[bool] = (
        None  # Is container update available
    )
    checked_at: Optional[datetime] = None  # Date of check for update
    updated_at: Optional[datetime] = None  # Date of last update
    created_at: Optional[datetime] = (
        None  # Date of creation of db entry
    )
    modified_at: Optional[datetime] = (
        None  # Date ofmodification db entry
    )


class ContainerPatchRequestBody(BaseModel):
    check_enabled: Optional[bool] = None
    update_enabled: Optional[bool] = None
