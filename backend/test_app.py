from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp.client_exceptions import ClientError
from fastapi import HTTPException

from backend.app import (
    agent_client_exception_handler,
    aiohttp_exception_handler,
    app,
    lifespan,
)
from backend.exception import TugAgentClientError


@pytest.mark.asyncio
async def test_lifespan_startup_order_and_shutdown(mocker):
    order: list[str] = []

    def track(name: str):
        async def _(*_args, **_kwargs):
            order.append(name)

        return _

    mocker.patch("backend.app.sync_local_agent_secret", side_effect=track("sync"))
    mocker.patch("backend.app.load_agents_on_init", side_effect=track("agents"))
    mocker.patch("backend.app.SettingsStorage.load_all", side_effect=track("settings"))
    mocker.patch("backend.app.schedule_jobs_on_init", side_effect=track("schedule"))
    mocker.patch(
        "backend.app.cleanup_all_stale_containers", side_effect=track("cleanup")
    )
    remove_all = mocker.patch(
        "backend.app.AgentClientManager.remove_all",
        new_callable=AsyncMock,
    )

    async with lifespan(app):
        assert order == ["sync", "agents", "settings", "schedule", "cleanup"]
        remove_all.assert_not_awaited()

    remove_all.assert_awaited_once()


@pytest.mark.asyncio
async def test_lifespan_continues_when_cleanup_fails(mocker):
    for name in (
        "sync_local_agent_secret",
        "load_agents_on_init",
        "SettingsStorage.load_all",
        "schedule_jobs_on_init",
    ):
        mocker.patch(f"backend.app.{name}", new_callable=AsyncMock)
    mocker.patch(
        "backend.app.cleanup_all_stale_containers",
        new_callable=AsyncMock,
        side_effect=RuntimeError("cleanup failed"),
    )
    log_exception = mocker.patch("backend.app.logging.exception")
    remove_all = mocker.patch(
        "backend.app.AgentClientManager.remove_all",
        new_callable=AsyncMock,
    )

    async with lifespan(app):
        log_exception.assert_called_once()

    remove_all.assert_awaited_once()


@pytest.mark.asyncio
async def test_agent_client_exception_becomes_424():
    exc = TugAgentClientError("agent down", "http://agent", "GET", 500, "nope")

    with pytest.raises(HTTPException) as err:
        await agent_client_exception_handler(MagicMock(), exc)

    assert err.value.status_code == 424
    assert err.value.detail == str(exc)


@pytest.mark.asyncio
async def test_aiohttp_exception_becomes_424(mocker):
    mocker.patch("backend.app.logging.exception")

    with pytest.raises(HTTPException) as err:
        await aiohttp_exception_handler(MagicMock(), ClientError("connection reset"))

    assert err.value.status_code == 424
    assert err.value.detail == "Unknown aiohttp error\nconnection reset"
