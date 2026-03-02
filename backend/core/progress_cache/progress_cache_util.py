import uuid
from backend.core.container_group.container_group_schemas import ContainerGroup
from backend.modules.hosts.hosts_model import HostsModel

ALL_CONTAINERS_STATUS_KEY = str(uuid.uuid4())


def get_host_cache_key(host: HostsModel) -> str:
    return f"{host.id}:{host.name}"


def get_group_cache_key(
    host: HostsModel, group: ContainerGroup
) -> str:
    return f"{get_host_cache_key(host)}:{group.name}"
