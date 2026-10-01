"""Importable helpers for backend tests.

Pytest discovers fixtures from ``conftest.py``. Factories that tests call
directly live here so modules do not import ``conftest``.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

from pytest_mock import MockerFixture

from shared.schemas.service_schemas import ServiceListItemSchema, ServiceReplicasSchema


def patch_async_session(
    mocker: MockerFixture,
    module: str,
    session: Any | None = None,
) -> Any:
    """Patch ``{module}.async_session_maker`` with an async context manager."""
    if session is None:
        session = MagicMock()
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=session)
    session_cm.__aexit__ = AsyncMock(return_value=None)
    mocker.patch(f"{module}.async_session_maker", return_value=session_cm)
    return session


def make_service(
    name: str = "web",
    image: str | None = None,
    service_id: str | None = None,
) -> ServiceListItemSchema:
    return ServiceListItemSchema(
        id=service_id if service_id is not None else f"id-{name}",
        name=name,
        image=image if image is not None else f"repo/{name}:latest",
        mode="replicated",
        replicas=ServiceReplicasSchema(running=1, desired=1),
    )
