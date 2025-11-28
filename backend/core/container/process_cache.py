from typing import Any, Generic, Mapping, Optional, TypedDict, TypeVar
from cachetools import TTLCache
from backend.core.container.schemas.check_result import (
    GroupCheckResult,
    HostCheckResult,
)
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
    result: Optional[
        GroupCheckResult
    ]  # Data wil be available only in the end


class HostCheckData(TypedDict, total=False):
    """Data of host container's check/update progress"""

    status: ECheckStatus  # Status of progress
    result: Optional[
        HostCheckResult
    ]  # Data will be available only in the end


class AllCheckData(TypedDict, total=False):
    """Data of all host's container's check/update progress"""

    status: ECheckStatus  # Status of progress
    result: Optional[
        dict[int, HostCheckResult]
    ]  # Data will be available only in the end


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
