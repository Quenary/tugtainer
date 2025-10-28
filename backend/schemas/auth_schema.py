from pydantic import BaseModel, field_validator
from typing import Dict, Any, Optional
from .validators import password_validator


class PasswordSetRequestBody(BaseModel):
    password: str
    confirm_password: str

    @field_validator("password", "confirm_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return password_validator(v)


class OIDCConfigResponse(BaseModel):
    enabled: bool
    client_id: Optional[str] = None
    redirect_uri: Optional[str] = None
    scopes: Optional[str] = None


class OIDCLoginResponse(BaseModel):
    authorization_url: str
    state: str