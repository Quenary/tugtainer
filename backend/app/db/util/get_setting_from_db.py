from sqlalchemy import select
from app.enums import ESettingKey
from app.db import async_session_maker, SettingModel


async def get_setting_from_db(key: ESettingKey) -> SettingModel:
    async with async_session_maker() as session:
        stmt = (
            select(SettingModel)
            .where(SettingModel.key == key)
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalars().first()
