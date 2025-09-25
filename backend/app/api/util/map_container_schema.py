from app.db import ContainersModel
from app.schemas import ContainerGetResponseBody
from docker.models.containers import Container
from app.helpers import is_self_container


def map_container_schema(
    d_cont: Container,
    db_cont: ContainersModel | None,
) -> ContainerGetResponseBody:
    """
    Map docker container data and db container data
    to api response schema
    """
    _item = ContainerGetResponseBody(
        name=str(d_cont.name),
        short_id=d_cont.short_id,
        ports=d_cont.ports,
        status=d_cont.attrs["State"]["Status"],
        health=str(d_cont.health),
        is_self=is_self_container(d_cont),
    )
    if db_cont:
        _item.check_enabled = db_cont.check_enabled
        _item.update_enabled = db_cont.update_enabled
        _item.update_available = db_cont.update_available
        _item.checked_at = db_cont.checked_at
        _item.updated_at = db_cont.updated_at
        _item.created_at = db_cont.created_at
        _item.modified_at = db_cont.modified_at

    return _item
