from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException, status

from backend.config import Config
from backend.exception import TugUrlValidationSSRFError
from backend.modules.settings.settings_enum import ESettingKey, ESettingType
from backend.util.validate_url_against_ssrf import validate_url_against_ssrf


def get_setting_typed_value(value: str, value_type: str) -> bool | float | int | str:
    """
    Helper func to get typed app setting value
    """
    try:
        if value_type == ESettingType.BOOL:
            return value.lower() == "true"
        elif value_type == ESettingType.FLOAT:
            return float(value)
        elif value_type == ESettingType.INT:
            return int(value)
        return value
    except Exception:
        return value


def split_notification_urls(urls: str) -> set[str]:
    return {url.strip() for url in urls.splitlines() if url.strip()}


def validate_notification_urls(urls: Any) -> None:
    """Quick sync validation of notification URLs"""
    if not isinstance(urls, str):
        raise ValueError(f"Invalid {ESettingKey.NOTIFICATION_URLS}, expected string.")

    for url in split_notification_urls(urls):
        parsed = urlparse(url)

        if not parsed.scheme:
            raise ValueError(f"Missing scheme in notification URL: {url}")

        if (
            Config.NOTIFICATION_ALLOW_SCHEMES
            and parsed.scheme not in Config.NOTIFICATION_ALLOW_SCHEMES
        ):
            raise ValueError(
                f"Notification scheme '{parsed.scheme}' not allowed."
                "\nYou can change this behavior through "
                "NOTIFICATION_ALLOW_SCHEMES environment variable."
            )


async def validate_notification_urls_against_ssrf(urls: str) -> None:
    """
    Helper func for validating notification URLs against SSRF.
    Raises only on TugUrlValidationSSRFError and ignores other
    exceptions because apprise URL may be invalid as standard URL
    (missing or invalid hostname, port, etc)
    """
    for url in split_notification_urls(urls):
        try:
            await validate_url_against_ssrf(
                url,
                Config.NOTIFICATION_ALLOW_NETWORKS,
                Config.NOTIFICATION_ALLOW_ENDPOINTS,
            )
        except TugUrlValidationSSRFError as e:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"{e}"
                "\nYou can change this behavior through "
                "NOTIFICATION_ALLOW_NETWORKS and NOTIFICATION_ALLOW_ENDPOINTS "
                "environment variables.",
            ) from e
        except Exception:
            pass
