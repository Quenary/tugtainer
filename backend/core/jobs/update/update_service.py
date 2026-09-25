import logging
from typing import Final

from sqlalchemy import select

from backend.core.agent_client import AgentClient
from backend.core.jobs.jobs_results import ServiceJobResult
from backend.core.jobs.jobs_tracker import HostJobTracker
from backend.db.session import async_session_maker
from backend.enums.job_status_enum import EJobStatus
from backend.modules.hosts.hosts_model import HostsModel
from backend.modules.services.services_model import SwarmServicesModel
from backend.util.now import now
from shared.schemas.service_schemas import (
    ServiceListItemSchema,
    ServiceUpdateRequestBody,
)


async def run_update_service_job(
    client: AgentClient,
    host: HostsModel,
    service: ServiceListItemSchema,
    tracker: HostJobTracker | None = None,
) -> ServiceJobResult:
    result: Final = ServiceJobResult(
        service_name=service.name,
        service_image=service.image,
        service_id=service.id,
    )
    logger: Final = logging.getLogger(f"run_update_service_job.{service.name}")

    def _slot(status: EJobStatus, slot_result: ServiceJobResult | None = None) -> None:
        if tracker:
            tracker.set_container(service.name, status, slot_result)

    async with async_session_maker() as session:
        try:
            logger.info("Starting swarm service update")
            _slot(EJobStatus.PREPARING)

            _slot(EJobStatus.UPDATING)
            await client.service.update(
                ServiceUpdateRequestBody(
                    service_id=service.id,
                    image=service.image,
                )
            )

            # Update DB
            s_db: Final = (
                await session.execute(
                    select(SwarmServicesModel)
                    .where(
                        SwarmServicesModel.host_id == host.id,
                        SwarmServicesModel.name == service.name,
                    )
                    .limit(1)
                )
            ).scalar_one_or_none()

            if s_db:
                s_db.update_available = False
                s_db.updated_at = now()
                await session.commit()

            result.result = "updated"
            logger.info(f"Service {service.name} successfully updated")
            _slot(EJobStatus.DONE, result)
            return result
        except Exception:
            logger.exception("Failed to update swarm service")
            result.result = "failed"
            _slot(EJobStatus.ERROR, result)
            return result
