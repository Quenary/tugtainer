from inspect import signature
import logging
from sqlalchemy import select
from backend.db.session import async_session_maker
from backend.db.models import HostsModel
from backend.schemas import HostInfo
from .agent_client import AgentClient


async def load_hosts_on_init():
    """Init hosts from db"""
    async with async_session_maker() as session:
        stmt = select(HostsModel).where(HostsModel.enabled == True)
        result = await session.execute(stmt)
        hosts = result.scalars().all()
        for h in hosts:
            try:
                HostsManager.set_client(h)
                logging.info(f"Docker host '{h.name}' loaded.")
            except Exception as e:
                logging.error(f"Error loading docker host '{h.name}'")
                logging.exception(e)


class HostsManager:
    """Class for managing multiple docker hosts"""

    _INSTANCE = None
    _HOST_CLIENTS: dict[int, AgentClient] = {}

    def __new__(cls, *args, **kwargs):
        if cls._INSTANCE is None:
            cls._INSTANCE = super().__new__(cls)
        return cls._INSTANCE

    @classmethod
    def set_client(cls, host: HostsModel):
        cls.remove_client(host.id)
        cls._HOST_CLIENTS[host.id] = cls._create_client(host)

    @classmethod
    def get_host_client(cls, host: HostsModel) -> AgentClient:
        if host.id in cls._HOST_CLIENTS:
            return cls._HOST_CLIENTS[host.id]
        client = cls._create_client(host)
        cls._HOST_CLIENTS[host.id] = cls._create_client(host)
        return client

    @classmethod
    def _create_client(cls, host: HostsModel) -> AgentClient:
        info = HostInfo.model_validate(host)
        allowed_keys = signature(AgentClient.__init__).parameters
        filtered = {
            k: v
            for k, v in info.model_dump(exclude_unset=True).items()
            if k in allowed_keys and v
        }
        return AgentClient(**filtered)

    @classmethod
    def get_all(cls) -> list[tuple[int, AgentClient]]:
        """
        Get all registered host clients.
        :returns: list of tuple(host_id, client)
        """
        return list[tuple[int, AgentClient]](
            cls._HOST_CLIENTS.items()
        )

    @classmethod
    def remove_client(cls, id: int):
        cls._HOST_CLIENTS.pop(id, None)
