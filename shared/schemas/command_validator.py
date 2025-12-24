from typing import Any, Callable, TypedDict, cast
from ipaddress import ip_address
import re

DOCKER_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$")


def validate_docker_name(value: str) -> None:
    if not DOCKER_NAME_RE.fullmatch(value):
        raise ValueError(f"Invalid docker identifier: {value}")


ALIAS_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,62}$")


def validate_alias(value: str) -> None:
    if not ALIAS_RE.match(value):
        raise ValueError(f"Invalid alias: {value}")


def validate_ip(value: str) -> None:
    ip_address(value)


class CmdSchema(TypedDict):
    # Flags and validators
    flags: dict[str, Callable[[str], Any]]
    # Positional validators
    # Length should be validated as well
    positional: list[Callable[[str], Any]]


COMMAND_SCHEMAS: dict[tuple[str, ...], CmdSchema] = {
    ("network", "connect"): {
        "flags": {
            "--alias": validate_alias,
            "--ip": validate_ip,
            "--ip6": validate_ip,
        },
        "positional": [
            validate_docker_name,  # network
            validate_docker_name,  # container
        ],
    },
}


def resolve_command_schema(
    cmd: list[str],
) -> tuple[tuple[str, ...], CmdSchema]:
    if not cmd:
        raise ValueError("Empty command")

    # Find longest prefix
    for size in range(len(cmd), 0, -1):
        key = tuple(cmd[:size])
        schema = COMMAND_SCHEMAS.get(key)
        if schema:
            return key, schema

    raise ValueError(f"Command not allowed: {cmd}")


def command_validator(cmd: list[str]) -> list[str]:
    key, schema = resolve_command_schema(cmd)
    flags = schema["flags"]
    positional_validators = schema["positional"]

    positional: list[str] = []
    i = len(key)

    while i < len(cmd):
        part = cmd[i]

        if part.startswith("-"):
            if positional:
                raise ValueError(
                    f"Flag {part} must come before positional args"
                )
            if part not in flags:
                raise ValueError(f"Unknown flag: {part}")

            if i + 1 >= len(cmd):
                raise ValueError(f"Flag {part} requires value")

            value = cmd[i + 1]
            flags[part](value)  # validation
            i += 2
        else:
            positional.append(part)
            i += 1

    if len(positional) != len(positional_validators):
        raise ValueError(
            f"Expected {len(positional_validators)} positional args, got {len(positional)}"
        )

    for value, validator in zip(positional, positional_validators):
        validator(value)

    return cmd
