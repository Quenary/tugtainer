import pytest
from pydantic import ValidationError

from shared.schemas.container_schemas import ExecContainerRequestBodySchema


def test_exec_container_request_body_schema_accepts_command():
    body = ExecContainerRequestBodySchema(command="pg_dump -U postgres mydb")
    assert body.command == "pg_dump -U postgres mydb"


def test_exec_container_request_body_schema_rejects_empty_command():
    with pytest.raises(ValidationError):
        ExecContainerRequestBodySchema(command="")
