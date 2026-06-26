from datetime import datetime

from pydantic import BaseModel, field_validator, model_validator

from backend.modules.settings.settings_enum import ESettingKey
from backend.modules.settings.settings_util import validate_notification_urls

from .settings_validators import validate_cron_expr, validate_timezone


class SettingsBase(BaseModel):
    key: str
    value: bool | int | float | str


class SettingsPatchRequestItem(SettingsBase):
    @model_validator(mode="after")
    def validate_setting(self):
        if self.key == ESettingKey.CHECK_CRONTAB_EXPR:
            _ = validate_cron_expr(str(self.value))
            return self
        elif self.key == ESettingKey.UPDATE_CRONTAB_EXPR:
            _ = validate_cron_expr(str(self.value))
            return self
        elif self.key == ESettingKey.TIMEZONE:
            _ = validate_timezone(str(self.value))
            return self
        elif self.key == ESettingKey.REGISTRY_REQ_DELAY:
            if isinstance(self.value, int) and self.value > 0:
                return self
            raise ValueError(
                f"Invalid {ESettingKey.REGISTRY_REQ_DELAY}, expected positive integer."
            )
        elif self.key == ESettingKey.NOTIFICATION_URLS:
            validate_notification_urls(self.value)
            return self
        else:
            return self


class SettingsGetResponseItem(SettingsBase):
    value_type: str
    modified_at: datetime


class TestNotificationRequestBody(BaseModel):
    title_template: str
    body_template: str
    urls: str

    @field_validator("urls")
    @classmethod
    def validate_urls(cls, value: str) -> str:
        validate_notification_urls(value)
        return value
