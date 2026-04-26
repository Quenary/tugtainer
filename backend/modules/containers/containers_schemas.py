from datetime import datetime

from pydantic import BaseModel
from python_on_whales.components.container.models import (
    ContainerInspectResult,
    PortBinding,
)


class ContainersListItem(BaseModel):
    name: str  # name of the container
    container_id: str  # id of the container
    image: str | None  # image of the container
    ports: dict[str, list[PortBinding] | None] | None
    status: str | None
    exit_code: int | None
    health: str | None
    protected: bool  # Whether container labeled with dev.quenary.tugtainer.protected=true
    host_id: int  # host id is also stored in db, but it must be always defined
    # Those keys stored in db, but might be undefined for new containers
    id: int | None = None  # id of the row
    check_enabled: bool | None = (
        None  # Is check for update enabled
    )
    update_enabled: bool | None = None  # Is auto update enabled
    update_available: bool | None = (
        None  # Is container update available
    )
    checked_at: datetime | None = None  # Date of check for update
    updated_at: datetime | None = None  # Date of last update
    created_at: datetime | None = (
        None  # Date of creation of db entry
    )
    modified_at: datetime | None = (
        None  # Date ofmodification db entry
    )


class ContainerGetResponseBody(BaseModel):
    item: ContainersListItem | None = None
    inspect: ContainerInspectResult


class ContainerPatchRequestBody(BaseModel):
    check_enabled: bool | None = None
    update_enabled: bool | None = None
