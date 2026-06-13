from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel
from python_on_whales.components.container.models import (
    ContainerInspectResult,
    PortBinding,
)

from backend.core.container_util.get_container_health_status_str import (
    get_container_health_status_str,
)
from backend.core.container_util.is_protected_container import is_protected_container
from backend.modules.containers.containers_model import ContainersModel

if TYPE_CHECKING:
    from .containers_model import ContainersModel


class ContainersListItem(BaseModel):
    name: str  # name of the container
    container_id: str  # id of the container
    image: str | None  # image of the container
    ports: dict[str, list[PortBinding] | None] | None
    status: str | None
    exit_code: int | None
    health: str | None
    protected: (
        bool  # Whether container labeled with dev.quenary.tugtainer.protected=true
    )
    host_id: int  # host id is also stored in db, but it must be always defined
    # Those keys stored in db, but might be undefined for new containers
    id: int | None = None  # id of the row
    check_enabled: bool | None = None  # Is check for update enabled
    update_enabled: bool | None = None  # Is auto update enabled
    update_available: bool | None = None  # Is container update available
    checked_at: datetime | None = None  # Date of check for update
    updated_at: datetime | None = None  # Date of last update
    created_at: datetime | None = None  # Date of creation of db entry
    modified_at: datetime | None = None  # Date ofmodification db entry

    @classmethod
    def from_sources(
        cls,
        host_id: int,
        docker_cont: "ContainerInspectResult",
        db_cont: "ContainersModel | None",
    ) -> "ContainersListItem":
        data = {
            "host_id": host_id,
            "name": docker_cont.name or "",
            "container_id": docker_cont.id or "",
            "image": docker_cont.config.image if docker_cont.config else None,
            "ports": docker_cont.host_config.port_bindings
            if docker_cont.host_config
            else None,
            "status": docker_cont.state.status if docker_cont.state else None,
            "exit_code": docker_cont.state.exit_code if docker_cont.state else None,
            "health": get_container_health_status_str(docker_cont),
            "protected": is_protected_container(docker_cont),
        }
        if db_cont:
            data.update(
                {
                    "id": db_cont.id,
                    "check_enabled": db_cont.check_enabled,
                    "update_enabled": db_cont.update_enabled,
                    "update_available": db_cont.update_available,
                    "checked_at": db_cont.checked_at,
                    "updated_at": db_cont.updated_at,
                    "created_at": db_cont.created_at,
                    "modified_at": db_cont.modified_at,
                }
            )
        return cls.model_validate(data)


class ContainerGetResponseBody(BaseModel):
    item: ContainersListItem | None = None
    inspect: ContainerInspectResult


class ContainerPatchRequestBody(BaseModel):
    check_enabled: bool | None = None
    update_enabled: bool | None = None
