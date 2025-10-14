from app.db import ContainersModel
from app.schemas import ContainerGetResponseBody
from app.helpers import is_self_container
from python_on_whales import Container
from app.core.container.util import get_container_health_status_str


def map_container_schema(
    host_id: int,
    d_cont: Container,
    db_cont: ContainersModel | None,
) -> ContainerGetResponseBody:
    """
    Map docker container data and db container data
    to api response schema
    """
    _item = ContainerGetResponseBody(
        name=d_cont.name,
        image=d_cont.config.image if d_cont.config.image else None,
        container_id=d_cont.id,
        ports=d_cont.host_config.port_bindings,
        status=d_cont.state.status,
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
