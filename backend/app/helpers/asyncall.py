import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, ParamSpec, TypeVar
from asyncio import AbstractEventLoop
from app.enums import ESettingKey
from .settings_storage import SettingsStorage

EXECUTOR = ThreadPoolExecutor(7)

P = ParamSpec("P")
R = TypeVar("R")


async def asyncall(
    func: Callable[P, R],
    asyncall_timeout: int | None = None,
    asyncall_loop: AbstractEventLoop | None = None,
    *args: P.args,
    **kwargs: P.kwargs,
) -> R:
    """
    Run sync func asynchronously.
    :param asyncall_timeout: timeout to an error (default is value of ESettingKey.DOCKER_TIMEOUT)
    :param asyncall_loop: set loop explicitly (default is running loop)
    """
    if not asyncall_timeout:
        asyncall_timeout = SettingsStorage.get(
            ESettingKey.DOCKER_TIMEOUT
        )
    if not asyncall_loop:
        asyncall_loop = asyncio.get_running_loop()
    return await asyncio.wait_for(
        asyncall_loop.run_in_executor(
            EXECUTOR, lambda: func(*args, **kwargs)
        ),
        asyncall_timeout,
    )
