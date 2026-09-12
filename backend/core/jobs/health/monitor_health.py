from backend.core.jobs.health.check_health import check_all_containers_health
from backend.core.jobs.health.rotate_history import rotate_health_history


async def run_health_monitor() -> None:
    """
    Periodic health monitor job: check all containers health and rotate history.
    """
    await check_all_containers_health()
    await rotate_health_history()
