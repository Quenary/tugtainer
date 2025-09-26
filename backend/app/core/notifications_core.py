import logging
import apprise
from typing import cast
from sqlalchemy import select
from app.db.session import async_session_maker
from app.db.models.settings_model import SettingModel
from app.enums.settings_enum import ESettingKey

_url_sentinel = object()


async def send_notification(
    title: str, body: str, url: str | None = cast(None, _url_sentinel)
):
    async with async_session_maker() as session:
        _url = url
        if url is _url_sentinel:
            stmt = (
                select(SettingModel.value)
                .where(
                    SettingModel.key == ESettingKey.NOTIFICATION_URL
                )
                .limit(1)
            )
            result = await session.execute(stmt)
            _url = result.scalar_one_or_none()

        if _url:
            _apprise = apprise.Apprise()
            _apprise.add(_url)
            result = await _apprise.async_notify(
                title=title, body=body
            )
            if result == False:
                message = "Failed to send notification"
                logging.error(message)
                raise Exception(message)
        else:
            message = "Failed to send notification. URL is undefined."
            logging.error(message)
            raise Exception(message)
