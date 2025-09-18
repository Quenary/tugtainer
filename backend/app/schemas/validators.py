import re


def password_validator(value: str) -> str:
    """Validate password string"""
    if not re.search(r"[A-Z]", value):
        raise ValueError("The password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", value):
        raise ValueError("The password must contain at least one lowercase letter.")
    if not re.search(r"\d", value):
        raise ValueError("The password must contain at least one number.")
    return value
