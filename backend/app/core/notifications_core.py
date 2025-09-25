import logging
import apprise
from sqlalchemy import select
from app.db.session import async_session_maker
from app.db.models.settings_model import SettingModel
from app.enums.settings_enum import ESettingKey


async def send_notification(
    title: str,
    body: str,
):
    async with async_session_maker() as session:
        stmt = (
            select(SettingModel.value)
            .where(SettingModel.key == ESettingKey.NOTIFICATION_URL)
            .limit(1)
        )
        result = await session.execute(stmt)
        url = result.scalar_one_or_none()
        if url:
            _apprise = apprise.Apprise()
            _apprise.add(url)
            result = _apprise.notify(title=title, body=body)
            if result == False:
                message = "Failed to send notification"
                logging.error(message)
                raise Exception(message)
        else:
            message = "Failed to send notification. URL is undefined."
            logging.error(message)
            raise Exception(message)
