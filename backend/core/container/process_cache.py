from typing import Any, Generic, Mapping, TypedDict, TypeVar
from cachetools import TTLCache
from backend.enums import ECheckStatus
import uuid
from .container_group import ContainerGroup
from backend.db.models import HostsModel


ALL_CONTAINERS_STATUS_KEY = str(uuid.uuid4())


def get_host_cache_key(host: HostsModel) -> str:
    return f"{host.id}:{host.name}"


def get_group_cache_key(
    host: HostsModel, group: ContainerGroup
) -> str:
    return f"{get_host_cache_key(host)}:{group.name}"


_CACHE = TTLCache(maxsize=10, ttl=600)


class GroupCheckData(TypedDict, total=False):
    """Data of containers group check/update progress"""

    status: ECheckStatus  # Status of progress


class HostCheckData(GroupCheckData, total=False):
    """Data of host container's check/update progress"""

    available: int  # Count of not updated containers (check only)
    updated: int  # count of updated containers
    rolled_back: int  # count of rolled-back after fail
    failed: int  # count of failed updates


class AllCheckData(HostCheckData, total=False):
    """Data of all host's container's check/update progress"""

    pass


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
