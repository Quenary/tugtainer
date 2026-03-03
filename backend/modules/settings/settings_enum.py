from enum import Enum


class ESettingKey(str, Enum):
    """
    Enum of app settings keys.
    It is helper, do not use for validation.
    """

    CHECK_CRONTAB_EXPR = "CHECK_CRONTAB_EXPR"
    UPDATE_CRONTAB_EXPR = "UPDATE_CRONTAB_EXPR"
    PULL_BEFORE_CHECK = "PULL_BEFORE_CHECK"
    REGISTRY_REQ_DELAY = "REGISTRY_REQ_DELAY"
    TIMEZONE = "TIMEZONE"
    NOTIFICATION_URLS = "NOTIFICATION_URLS"
    NOTIFICATION_TITLE_TEMPLATE = "NOTIFICATION_TITLE_TEMPLATE"
    NOTIFICATION_BODY_TEMPLATE = "NOTIFICATION_BODY_TEMPLATE"
    UPDATE_ONLY_RUNNING = "UPDATE_ONLY_RUNNING"


class ESettingType(str, Enum):
    """
    Enum of app settings types.
    It is helper, do not use for validation.
    """

    BOOL = "bool"
    FLOAT = "float"
    INT = "int"
    STR = "str"
