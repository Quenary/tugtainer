import pytest
from pydantic import ValidationError

from shared.schemas.command_schemas import RunCommandRequestBodySchema
from shared.schemas.command_validator import command_validator, validate_link

# Command from https://github.com/Quenary/tugtainer/issues/225
ISSUE_225_COMMAND = [
    "network",
    "connect",
    "--alias",
    "nextcloud-app-1",
    "--alias",
    "app",
    "--link",
    "nextcloud-db-1:db",
    "--link",
    "nextcloud-db-1:db-1",
    "--link",
    "nextcloud-db-1:nextcloud-db-1",
    "vpnnet",
    "nextcloud-app-1",
]


def test_validate_link_accepts_name_and_alias():
    validate_link("nextcloud-db-1:db")


def test_validate_link_accepts_name_only():
    validate_link("nextcloud-db-1")


@pytest.mark.parametrize(
    "value",
    ["", ":", ":db", "db:", "../evil:db", "db:../alias"],
)
def test_validate_link_rejects_invalid_values(value: str):
    with pytest.raises(ValueError):
        validate_link(value)


def test_network_connect_allows_link_flag():
    assert command_validator(ISSUE_225_COMMAND) == ISSUE_225_COMMAND


def test_run_command_schema_accepts_network_connect_link():
    body = RunCommandRequestBodySchema(command=ISSUE_225_COMMAND)
    assert body.command == ISSUE_225_COMMAND


def test_run_command_schema_still_rejects_unknown_flag():
    with pytest.raises(ValidationError, match="Unknown flag"):
        RunCommandRequestBodySchema(
            command=["network", "connect", "--foo", "bar", "net", "app"]
        )
