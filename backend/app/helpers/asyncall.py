import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, ParamSpec, TypeVar, cast
from asyncio import AbstractEventLoop
from app.enums import ESettingKey
from .settings_storage import SettingsStorage
from app.exception import TugAsyncallNoLoopException

EXECUTOR = ThreadPoolExecutor(7)

P = ParamSpec("P")
R = TypeVar("R")

_timeout_sentinel = object()


async def asyncall(
    func: Callable[P, R],
    asyncall_timeout: int | None = cast(None, _timeout_sentinel),
    asyncall_loop: AbstractEventLoop | None = None,
    *args: P.args,
    **kwargs: P.kwargs,
) -> R:
    """
    Run sync func asynchronously with ThreadPoolExecutor.
    :param asyncall_timeout: timeout to an error (if not explicitly None, then default is ESettingKey.DOCKER_TIMEOUT)
    :param asyncall_loop: set loop explicitly (default is asyncio.get_event_loop())
    """
    if asyncall_timeout is _timeout_sentinel:
        asyncall_timeout = SettingsStorage.get(
            ESettingKey.DOCKER_TIMEOUT
        )
    if not asyncall_loop:
        asyncall_loop = asyncio.get_event_loop()
    if asyncall_timeout:
        return await asyncio.wait_for(
            asyncall_loop.run_in_executor(
                EXECUTOR, lambda: func(*args, **kwargs)
            ),
            asyncall_timeout,
        )
    else:
        return await asyncall_loop.run_in_executor(
            EXECUTOR, lambda: func(*args, **kwargs)
        )
