from typing import TypedDict
from app.db import (
    async_session_maker,
    insert_or_update_container,
    ContainerInsertOrUpdateData,
)


async def update_container_db_data(
    name: str, data: ContainerInsertOrUpdateData
):
    """Helper for updating container db data"""
    async with async_session_maker() as session:
        await insert_or_update_container(session, name, data)
