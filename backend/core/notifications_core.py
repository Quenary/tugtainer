import logging
import apprise
from apprise.exception import AppriseException
from typing import cast
from sqlalchemy import select
from backend.db.session import async_session_maker
from backend.db.models.settings_model import SettingModel
from backend.enums.settings_enum import ESettingKey
from backend.exception import TugException

_url_sentinel = object()


async def send_notification(
    title: str, body: str, url: str | None = cast(None, _url_sentinel)
):
    async with async_session_maker() as session:
        logging.info(f"Sending notification")
        logging.debug(f"Title: {title}")
        logging.debug(f"Body: {body}")

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
            try:
                _apprise = apprise.Apprise()
                _apprise.add(_url)
                result = await _apprise.async_notify(
                    title=title, body=body, interpret_escapes=True
                )
                if result == False:
                    message = "Failed to send notification, but no exception was raised by Apprise."
                    logging.error(message)
                    raise TugException(message)
            except AppriseException as e:
                logging.error(
                    "Failed to send notification. Apprise exception:"
                )
                logging.exception(e)
                raise e
        else:
            message = "Failed to send notification. URL is undefined."
            logging.error(message)
            raise TugException(message)
