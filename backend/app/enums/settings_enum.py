from enum import Enum


class ESettingKey(str, Enum):
    """
    Enum of app settings keys.
    It is helper, do not use for validation.
    """

    CRONTAB_EXPR = "CRONTAB_EXPR"
    NOTIFICATION_URL = "NOTIFICATION_URL"


class ESettingType(str, Enum):
    """
    Enum of app settings types.
    It is helper, do not use for validation.
    """

    BOOL = "bool"
    FLOAT = "float"
    INT = "int"
    STR = "str"
