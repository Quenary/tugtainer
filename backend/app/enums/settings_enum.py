from enum import Enum


class ESettingKey(str, Enum):
    """
    Enum of app settings keys.
    It is helper, do not use for validation.
    """

    CRONTAB_EXPR = "CRONTAB_EXPR"
    NOTIFICATION_URL = "NOTIFICATION_URL"
    TIMEZONE = "TIMEZONE"
    DOCKER_TIMEOUT = "DOCKER_TIMEOUT"
    
    # OIDC Settings
    OIDC_ENABLED = "OIDC_ENABLED"
    OIDC_WELL_KNOWN_URL = "OIDC_WELL_KNOWN_URL"
    OIDC_CLIENT_ID = "OIDC_CLIENT_ID"
    OIDC_CLIENT_SECRET = "OIDC_CLIENT_SECRET"
    OIDC_REDIRECT_URI = "OIDC_REDIRECT_URI"
    OIDC_SCOPES = "OIDC_SCOPES"


class ESettingType(str, Enum):
    """
    Enum of app settings types.
    It is helper, do not use for validation.
    """

    BOOL = "bool"
    FLOAT = "float"
    INT = "int"
    STR = "str"
