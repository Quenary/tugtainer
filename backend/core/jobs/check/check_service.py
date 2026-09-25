import asyncio
import logging
from typing import Final

from python_on_whales.components.image.models import ImageInspectResult
from sqlalchemy import select

from backend.core.agent_client import AgentClient
from backend.core.jobs.check.check_util import get_image_remote_digest
from backend.core.jobs.jobs_results import ContainerJobOutcome, ServiceJobResult
from backend.core.jobs.jobs_tracker import HostJobTracker
from backend.db.session import async_session_maker
from backend.enums.job_status_enum import EJobStatus
from backend.modules.hosts.hosts_model import HostsModel
from backend.modules.services.services_model import SwarmServicesModel
from backend.modules.settings.settings_enum import ESettingKey
from backend.modules.settings.settings_storage import SettingsStorage
from backend.util.jitter import jitter
from backend.util.now import now
from shared.schemas.image_schemas import (
    InspectImageRequestBodySchema,
    PullImageRequestBodySchema,
)
from shared.schemas.service_schemas import ServiceListItemSchema


async def run_check_service_job(
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
    delay: Final = SettingsStorage.get(ESettingKey.REGISTRY_REQ_DELAY)
    logger: Final = logging.getLogger(f"run_check_service_job.{service.name}")

    def _slot(status: EJobStatus, slot_result: ServiceJobResult | None = None) -> None:
        if tracker:
            tracker.set_container(service.name, status, slot_result)

    async with async_session_maker() as session:
        try:
            logger.info("Checking service update availability")
            _slot(EJobStatus.PREPARING)

            image_spec: Final = service.image
            if not image_spec:
                logger.warning("Missing service image. Exiting.")
                _slot(EJobStatus.DONE, result)
                return result
            logger.info(f"Image_spec is {image_spec}")

            # Swarm services often store image as "repo/image:tag@sha256:<digest>" when resolved.
            # Extract base tag for registry querying and pinned digest (if present).
            if "@" in image_spec:
                spec_base, pinned_digest = image_spec.split("@", 1)
            else:
                spec_base = image_spec
                pinned_digest = None

            local_digests: list[str] = []
            local_image: ImageInspectResult | None = None

            # 1. Try inspecting image on the manager host.
            # Services run tasks across the cluster, so manager node might not have the image cached.
            try:
                local_image = await client.image.inspect(
                    InspectImageRequestBodySchema(spec_or_id=image_spec)
                )
                if local_image and local_image.repo_digests:
                    local_digests = list(local_image.repo_digests)
            except Exception:
                logger.debug(
                    f"Image {image_spec} not found locally on manager node (tasks may run on workers)"
                )

            # 2. If image is not cached locally on manager, use Swarm's pinned digest from service spec
            if not local_digests and pinned_digest:
                logger.info(f"Using pinned digest from service image: {pinned_digest}")
                local_digests = [pinned_digest]

            # 3. Pull image only if PULL_BEFORE_CHECK setting is explicitly enabled
            if not local_digests and SettingsStorage.get(ESettingKey.PULL_BEFORE_CHECK):
                try:
                    logger.info(
                        f"Pulling image {spec_base} because PULL_BEFORE_CHECK is enabled"
                    )
                    local_image = await client.image.pull(
                        PullImageRequestBodySchema(image=spec_base)
                    )
                    if local_image and local_image.repo_digests:
                        local_digests = list(local_image.repo_digests)
                    await asyncio.sleep(jitter(delay))
                except Exception:
                    logger.exception(f"Failed to pull image {spec_base}")

            # 4. Protection against local-only images (built without registry digests)
            if not local_digests:
                logger.warning(
                    "Missing repo digests. Presumably a local image or image not found on manager. Exiting."
                )
                _slot(EJobStatus.DONE, result)
                return result

            result.local_image = local_image
            result.local_digests = local_digests
            logger.info(f"Local digests is {local_digests}")

            s_db = (
                await session.execute(
                    select(SwarmServicesModel)
                    .where(
                        SwarmServicesModel.host_id == host.id,
                        SwarmServicesModel.name == service.name,
                    )
                    .limit(1)
                )
            ).scalar_one_or_none()

            _slot(EJobStatus.CHECKING)

            # Pull image before digests if PULL_BEFORE_CHECK is enabled and not already pulled
            if (
                SettingsStorage.get(ESettingKey.PULL_BEFORE_CHECK)
                and not result.remote_image
            ):
                try:
                    logger.info("Pulling image before remote digests")
                    remote_image = await client.image.pull(
                        PullImageRequestBodySchema(image=spec_base)
                    )
                    result.remote_image = remote_image
                    await asyncio.sleep(jitter(delay))
                except Exception:
                    logger.exception(f"Failed to pull image {spec_base}")

            # Query remote registry for updated digest
            remote_digests: list[str] = []
            for d in local_digests:
                try:
                    rd = await get_image_remote_digest(spec_base, d)
                    if rd:
                        remote_digests = [rd]
                        break
                except Exception:
                    logger.exception(f"Failed to get remote digest for {spec_base} {d}")
                finally:
                    await asyncio.sleep(jitter(delay))

            result.remote_digests = remote_digests
            logger.info(f"Remote digests is {remote_digests}")

            result_lit: ContainerJobOutcome
            update_available: bool
            if not remote_digests:
                logger.warning(
                    "No remote digests obtained; skipping availability conclusion"
                )
                result_lit = None
                update_available = bool(s_db.update_available) if s_db else False
            elif any(
                all(rd not in ld for ld in local_digests) for rd in remote_digests
            ):
                if s_db and s_db.remote_digests == remote_digests:
                    result_lit = "available(notified)"
                else:
                    result_lit = "available"
                update_available = True
            else:
                result_lit = "not_available"
                update_available = False

            logger.info(f"Check result is {result_lit}")
            result.result = result_lit

            # Save state to database
            if s_db is None:
                s_db = SwarmServicesModel(
                    host_id=host.id,
                    service_id=service.id,
                    name=service.name,
                    image=service.image,
                )
                session.add(s_db)

            s_db.image = service.image
            s_db.service_id = service.id
            s_db.update_available = update_available
            s_db.checked_at = now()
            s_db.local_digests = local_digests
            s_db.remote_digests = remote_digests
            if local_image and local_image.id:
                s_db.image_id = str(local_image.id)

            await session.commit()
            _slot(EJobStatus.DONE, result)
            return result
        except Exception:
            logger.exception("Failed to check service")
            _slot(EJobStatus.ERROR, result)
            return result
