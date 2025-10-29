from pydantic import BaseModel, field_validator
from .validators import password_validator


class PasswordSetRequestBody(BaseModel):
    password: str
    confirm_password: str

    @field_validator("password", "confirm_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return password_validator(v)