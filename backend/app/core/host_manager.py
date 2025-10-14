from inspect import signature
import threading
import logging
from sqlalchemy import select
from app.schemas import HostInfo
from python_on_whales import DockerClient
from app.db import async_session_maker, HostModel


async def load_hosts_on_init():
    """Init hosts from db"""
    async with async_session_maker() as session:
        stmt = select(HostModel).where(HostModel.enabled == True)
        result = await session.execute(stmt)
        hosts = result.scalars().all()
        for h in hosts:
            try:
                info = HostInfo.model_validate(h)
                HostManager.set_client(info)
                logging.info(f"Docker host '{h.name}' loaded.")
            except Exception as e:
                logging.error(f"Error loading docker host '{h.name}'")
                logging.exception(e)


class HostManager:
    """Class for managing multiple docker hosts"""

    _INSTANCE = None
    _HOST_CLIENTS: dict[int, DockerClient] = {}

    def __new__(cls, *args, **kwargs):
        if cls._INSTANCE is None:
            cls._INSTANCE = super().__new__(cls)
        return cls._INSTANCE

    @classmethod
    def set_client(cls, info: HostInfo):
        cls.remove_client(info.id)
        cls._HOST_CLIENTS[info.id] = cls._create_client(info)

    @classmethod
    def get_host_client(cls, info: HostInfo) -> DockerClient:
        if info.id in cls._HOST_CLIENTS:
            return cls._HOST_CLIENTS[info.id]
        client = cls._create_client(info)
        cls._HOST_CLIENTS[info.id] = cls._create_client(info)
        return client

    @classmethod
    def _create_client(cls, info: HostInfo) -> DockerClient:
        allowed_keys = signature(DockerClient.__init__).parameters
        filtered = {
            k: v
            for k, v in info.model_dump(exclude_unset=True).items()
            if k in allowed_keys and v
        }
        return DockerClient(**filtered)

    @classmethod
    def get_all(cls) -> list[tuple[int, DockerClient]]:
        """
        Get all registered host clients.
        :returns: list of tuple(host_id, client)
        """
        return list[tuple[int, DockerClient]](
            cls._HOST_CLIENTS.items()
        )

    @classmethod
    def remove_client(cls, id: int):
        cls._HOST_CLIENTS.pop(id, None)
