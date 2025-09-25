from pydantic import BaseModel, RootModel, model_validator
from typing import Union, cast
from datetime import datetime
from app.enums.settings_enum import ESettingKey
from .validators import validate_cron_expr


class SettingsPatchRequestItem(BaseModel):
    key: str
    value: Union[bool, int, float, str]

    @model_validator(mode='after')
    def validate_setting(self):
        if self.key == ESettingKey.CRONTAB_EXPR:
            _ = validate_cron_expr(cast(str, self.value))
            return self
        else:
            return self


class SettingsGetResponseItem(SettingsPatchRequestItem):
    value_type: str
    modified_at: datetime