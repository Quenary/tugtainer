"""Agent API protocol shared by the agent and the backend.

``protocol`` is the major version of the agent HTTP API. 1.x and 2.x agents
are not compatible. ``version`` is the installed app version.
"""

from typing import Final

from pydantic import BaseModel

AGENT_PROTOCOL: Final = 2
AGENT_UPGRADE_MESSAGE: Final = "the agent must be upgraded to 2.x"


class AgentProtocol(BaseModel):
    version: str
    protocol: int


def read_installed_version(path: str = "/app/version") -> str:
    """Version file written into the image, or ``dev`` outside a release image."""
    try:
        with open(path) as file:
            text = file.readline().strip()
    except OSError:
        return "dev"
    return text or "dev"


def protocol_error(protocol: int | None) -> str | None:
    if protocol == AGENT_PROTOCOL:
        return None
    return AGENT_UPGRADE_MESSAGE
