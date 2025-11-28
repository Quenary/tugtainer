from enum import Enum


class ESettingKey(str, Enum):
    """
    Enum of app settings keys.
    It is helper, do not use for validation.
    """

    CRONTAB_EXPR = "CRONTAB_EXPR"
    TIMEZONE = "TIMEZONE"
    NOTIFICATION_URLS = "NOTIFICATION_URLS"
    NOTIFICATION_TITLE_TEMPLATE = "NOTIFICATION_TITLE_TEMPLATE"
    NOTIFICATION_BODY_TEMPLATE = "NOTIFICATION_BODY_TEMPLATE"


class ESettingType(str, Enum):
    """
    Enum of app settings types.
    It is helper, do not use for validation.
    """

    BOOL = "bool"
    FLOAT = "float"
    INT = "int"
    STR = "str"
