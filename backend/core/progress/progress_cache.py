from collections.abc import Mapping
from typing import Any

from cachetools import TTLCache

_CACHE = TTLCache(maxsize=10, ttl=600)


class ProgressCache[T:Mapping[Any, Any]]:
    """
    Helper class for check/update progress.
    If data argument is passed, the cache will be replaced.
    """

    def __init__(self, id: str, data: T | None = None) -> None:
        self._id = id
        if data:
            self.set(data)

    def get(self) -> T | None:
        return _CACHE.get(self._id)

    def set(self, data: T):
        _CACHE[self._id] = data

    def update(self, data: T):
        current = _CACHE.get(self._id) or {}
        _CACHE[self._id] = {**current, **data}
