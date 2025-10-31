from typing import cast
from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from backend.db.models import ContainersModel
from backend.schemas import ContainerGetResponseBody
from backend.helpers.self_container import is_self_container
from python_on_whales import Container
from backend.core.container.util import get_container_health_status_str


def map_container_schema(
    host_id: int,
    d_cont: ContainerInspectResult,
    db_cont: ContainersModel | None,
) -> ContainerGetResponseBody:
    """
    Map docker container data and db container data
    to api response schema
    """
    _item = ContainerGetResponseBody(
        name=d_cont.name if d_cont.name else "",
        image=(
            d_cont.config.image
            if d_cont.config and d_cont.config.image
            else None
        ),
        container_id=d_cont.id if d_cont.id else "",
        ports=(
            d_cont.host_config.port_bindings
            if d_cont.host_config
            else None
        ),
        status=d_cont.state.status if d_cont.state else None,
        exit_code=d_cont.state.exit_code if d_cont.state else None,
        health=get_container_health_status_str(d_cont),
        is_self=is_self_container(d_cont),
        host_id=host_id,
    )
    if db_cont:
        _item.id = db_cont.id
        _item.check_enabled = db_cont.check_enabled
        _item.update_enabled = db_cont.update_enabled
        _item.update_available = db_cont.update_available
        _item.checked_at = db_cont.checked_at
        _item.updated_at = db_cont.updated_at
        _item.created_at = db_cont.created_at
        _item.modified_at = db_cont.modified_at

    return _item
