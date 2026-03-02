import time
import asyncio
from functools import wraps
from typing import Callable, Any


def delay_to_minimum(min_seconds: float = 1):
    """
    Decorator for async functions
    that delays result if the execution was faster
    :param min_seconds minimum execution time in seconds
    """

    def decorator(func: Callable[..., Any]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.monotonic()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                elapsed = time.monotonic() - start
                delay = max(0, min_seconds - elapsed)
                if delay > 0:
                    await asyncio.sleep(delay)

        return wrapper

    return decorator
