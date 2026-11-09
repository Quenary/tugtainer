SWARM_SERVICE_ID_LABEL = "com.docker.swarm.service.id"
SWARM_SERVICE_NAME_LABEL = "com.docker.swarm.service.name"


def swarm_service_name(labels: dict[str, str] | None) -> str | None:
    """Name of the Swarm service that owns this container, or None."""
    if not labels or SWARM_SERVICE_ID_LABEL not in labels:
        return None
    name = (labels.get(SWARM_SERVICE_NAME_LABEL) or "").strip()
    service_id = (labels.get(SWARM_SERVICE_ID_LABEL) or "").strip()
    return name or service_id or "unknown"


def swarm_managed_reason(labels: dict[str, str] | None) -> str | None:
    """
    Why a Swarm task container must not be recreated, or None when it may be.

    Updating the task container would recreate it outside the service.
    The service update is the operation that replaces the task.
    """
    shown = swarm_service_name(labels)
    if shown is None:
        return None
    return f"is managed by Swarm service {shown}; update the service instead"
