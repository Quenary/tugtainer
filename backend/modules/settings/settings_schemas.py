from datetime import datetime

from pydantic import BaseModel, model_validator

from backend.modules.settings.settings_enum import ESettingKey

from .settings_validators import validate_cron_expr, validate_timezone


class SettingsPatchRequestItem(BaseModel):
    key: str
    value: bool | int | float | str

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
        else:
            return self


class SettingsGetResponseItem(SettingsPatchRequestItem):
    value_type: str
    modified_at: datetime


class TestNotificationRequestBody(BaseModel):
    title_template: str | None = None
    body_template: str | None = None
    urls: str | None = None
