import logging
from apprise import Apprise, NotifyFormat
from apprise.exception import AppriseException
from typing import Any, cast
from backend.config import Config
from backend.core.container.schemas.check_result import (
    ContainerCheckResult,
    HostCheckResult,
)
from backend.enums.settings_enum import ESettingKey
from backend.exception import TugException
import jinja2
from backend.helpers.settings_storage import SettingsStorage


def any_worthy(items: list[ContainerCheckResult]) -> bool:
    return any(
        item.result
        in [
            "available",
            "updated",
            "rolled_back",
            "failed",
        ]
        for item in items
    )


tt_sentinel = object()
bt_sentinel = object()
u_sentinel = object()


async def send_check_notification(
    results: list[HostCheckResult],
    title_template: str | None = cast(None, tt_sentinel),
    body_template: str | None = cast(None, bt_sentinel),
    urls: str | None = cast(None, u_sentinel),
):
    """
    Send check results notification.
    :param results: results of check/update process
    :param title_template: override title template
    :param body_template: override body template
    :param urls: override urls
    """
    try:
        _any_worthy = any(any_worthy(r.items) for r in results)
        if not _any_worthy:
            logging.info(
                "Nothing to report after check, skipping notification."
            )
        if title_template == tt_sentinel:
            title_template = SettingsStorage.get(
                ESettingKey.NOTIFICATION_TITLE_TEMPLATE
            )
        if body_template == bt_sentinel:
            body_template = SettingsStorage.get(
                ESettingKey.NOTIFICATION_BODY_TEMPLATE
            )
        if urls == u_sentinel:
            urls = SettingsStorage.get(ESettingKey.NOTIFICATION_URLS)

        if not urls:
            return
        _urls = [
            line.strip() for line in urls.splitlines() if line.strip()
        ]

        jinja2_env = jinja2.Environment(
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=False,
        )
        jinja2_env.filters["any_worthy"] = any_worthy
        context = {"results": results, "hostname": Config.HOSTNAME}

        title = None
        if title_template:
            _title_template = jinja2_env.from_string(title_template)
            title = _title_template.render(**context)
        body = None
        if body_template:
            _body_template = jinja2_env.from_string(body_template)
            body = _body_template.render(**context)

        return await send_notification(title, body, urls=_urls)
    except:
        pass


async def send_notification(
    title: str | None = None,
    body: str | None = None,
    body_format: NotifyFormat = NotifyFormat.MARKDOWN,
    urls: list[str] = [],
):
    logging.info(f"Sending notification")
    logging.debug(f"Title: {title}")
    logging.debug(f"Body: {body}")

    if urls:
        try:
            _apprise = Apprise()
            _apprise.add(cast(Any, urls))
            result = await _apprise.async_notify(
                title=title,
                body=body,
                body_format=body_format,
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
