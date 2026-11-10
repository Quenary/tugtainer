from backend.exception import TugAgentClientError
from backend.modules.hosts.hosts_model import HostsModel


def get_host_cache_key(host: HostsModel) -> str:
    return f"{host.id}:{host.name}"


def stale_swarm_error(exc: BaseException) -> bool:
    """Agent refused Swarm routes because this host is not a manager."""
    return isinstance(exc, TugAgentClientError) and exc.status == 503
