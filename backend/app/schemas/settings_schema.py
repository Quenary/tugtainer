from pydantic import BaseModel, RootModel, model_validator
from typing import Union, cast
from datetime import datetime
from app.enums.settings_enum import ESettingKey
from .validators import (
    validate_cron_expr, 
    validate_timezone,
    validate_oidc_well_known_url,
    validate_oidc_client_id,
    validate_oidc_scopes
)


class SettingsPatchRequestItem(BaseModel):
    key: str
    value: Union[bool, int, float, str]

    @model_validator(mode="after")
    def validate_setting(self):
        if self.key == ESettingKey.CRONTAB_EXPR:
            _ = validate_cron_expr(cast(str, self.value))
            return self
        elif self.key == ESettingKey.TIMEZONE:
            _ = validate_timezone(cast(str, self.value))
            return self
        elif self.key == ESettingKey.OIDC_WELL_KNOWN_URL:
            self.value = validate_oidc_well_known_url(cast(str, self.value))
            return self
        elif self.key == ESettingKey.OIDC_CLIENT_ID:
            self.value = validate_oidc_client_id(cast(str, self.value))
            return self
        elif self.key == ESettingKey.OIDC_SCOPES:
            self.value = validate_oidc_scopes(cast(str, self.value))
            return self
        else:
            return self


class SettingsGetResponseItem(SettingsPatchRequestItem):
    value_type: str
    modified_at: datetime


class TestNotificationRequestBody(BaseModel):
    url: str
