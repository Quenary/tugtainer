from pydantic import BaseModel


class RunCommandRequestBodySchema(BaseModel):
    command: list[str]
