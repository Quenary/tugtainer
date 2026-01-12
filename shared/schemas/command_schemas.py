from pydantic import BaseModel, field_validator
from .command_validator import command_validator


class RunCommandRequestBodySchema(BaseModel):
    command: list[str]

    @field_validator("command")
    @classmethod
    def validate_cmd(cls, cmd) -> list[str]:
        return command_validator(cmd)
