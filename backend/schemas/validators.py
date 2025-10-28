import re
from datetime import datetime
from cronsim import CronSim, CronSimError
from zoneinfo import available_timezones
from urllib.parse import urlparse


VALID_TIMEZONES = available_timezones()


def password_validator(value: str) -> str:
    """Validate password string"""
    if not re.search(r"[A-Z]", value):
        raise ValueError(
            "The password must contain at least one uppercase letter."
        )
    if not re.search(r"[a-z]", value):
        raise ValueError(
            "The password must contain at least one lowercase letter."
        )
    if not re.search(r"\d", value):
        raise ValueError(
            "The password must contain at least one number."
        )
    return value


def validate_cron_expr(expr: str) -> str:
    """
    Validate crontab expr.
    Return valid or raises value error
    """
    try:
        CronSim(expr, datetime.now())
    except CronSimError as e:
        raise ValueError(
            f"Invalid cron expression: {expr}. Details: {e}"
        )
    return expr


def validate_timezone(tz: str) -> str:
    if tz in VALID_TIMEZONES:
        return tz
    raise ValueError(f"Invalid timezone: {tz}")


def validate_oidc_well_known_url(url: str) -> str:
    """Validate OIDC well-known URL format"""
    if not url:
        return url  # Allow empty for disabled OIDC
    
    parsed = urlparse(url)
    if not parsed.scheme or parsed.scheme not in ['http', 'https']:
        raise ValueError("OIDC well-known URL must start with http:// or https://")
    
    if not parsed.netloc:
        raise ValueError("Invalid OIDC well-known URL format")
    
    # Ensure it ends with the well-known path or allow custom paths
    if not url.endswith('/.well-known/openid_configuration') and '/.well-known/' not in url:
        raise ValueError("OIDC URL should point to a well-known configuration endpoint")
    
    return url


def validate_oidc_client_id(client_id: str) -> str:
    """Validate OIDC Client ID"""
    if not client_id:
        return client_id  # Allow empty for disabled OIDC
    
    # Basic validation - client IDs are typically alphanumeric with some special chars
    if not re.match(r'^[a-zA-Z0-9._-]+$', client_id):
        raise ValueError("OIDC Client ID contains invalid characters")
    
    return client_id


def validate_oidc_scopes(scopes: str) -> str:
    """Validate OIDC scopes"""
    if not scopes:
        return "openid"  # Default to openid scope
    
    # Split scopes and validate each one
    scope_list = scopes.split()
    valid_scope_pattern = r'^[a-zA-Z0-9._:-]+$'
    
    for scope in scope_list:
        if not re.match(valid_scope_pattern, scope):
            raise ValueError(f"Invalid OIDC scope: {scope}")
    
    # Ensure 'openid' is always included
    if 'openid' not in scope_list:
        scope_list.insert(0, 'openid')
        scopes = ' '.join(scope_list)
    
    return scopes
