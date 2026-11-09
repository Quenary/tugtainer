from backend.exception import TugAgentClientError
from shared.agent_protocol import AGENT_UPGRADE_MESSAGE, protocol_error


async def agent_protocol_error(client) -> str | None:
    """Return the upgrade message when this agent cannot take an update.

    A connection failure stays a ``TugAgentClientError``. A missing version
    route (404) and any protocol other than 2 are the upgrade message.
    """
    try:
        payload = await client.public.version()
    except TugAgentClientError as exc:
        if exc.status == 404:
            return AGENT_UPGRADE_MESSAGE
        raise
    protocol = getattr(payload, "protocol", None)
    return protocol_error(protocol if isinstance(protocol, int) else None)
