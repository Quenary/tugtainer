from typing import TypedDict
from app.db.session import async_session_maker
from app.db.util import (
    insert_or_update_container,
    ContainerInsertOrUpdateData,
)


async def update_container_db_data(
    host_id: int, name: str, data: ContainerInsertOrUpdateData
):
    """Helper for updating container db data"""
    async with async_session_maker() as session:
        await insert_or_update_container(session, host_id, name, data)
