from typing import Any, Generic, Mapping, TypedDict, TypeVar, Union
from cachetools import TTLCache
from app.enums import ECheckStatus


_CACHE = TTLCache(maxsize=10, ttl=600)


class ContainerCheckData(TypedDict, total=False):
    """Data of single container check/update progress"""

    status: ECheckStatus  # Status of progress


class AllContainersCheckData(ContainerCheckData, total=False):
    """Data of all containers check/update progress"""

    available: int  # Count of not updated containers (check only)
    updated: int  # count of updated containers
    rolledback: int  # count of rolled-back after fail
    failed: int  # count of failed updates


T = TypeVar("T", bound=Mapping[Any, Any])


class ProcessCache(Generic[T]):
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
