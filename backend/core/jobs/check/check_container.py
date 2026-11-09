import asyncio
import logging
from typing import Final

from sqlalchemy import select

from backend.core.agent_client import AgentClient
from backend.core.container_util.get_container_image_spec import (
    get_container_image_spec,
)
from backend.core.jobs.check.check_util import (
    assess_image_update,
    image_is_local_build,
)
from backend.core.jobs.jobs_results import (
    ContainerJobOutcome,
    ContainerJobResult,
)
from backend.core.jobs.jobs_tracker import HostJobTracker
from backend.db.session import async_session_maker
from backend.enums.job_status_enum import EJobStatus
from backend.modules.containers.containers_model import (
    ContainersModel,
)
from backend.modules.containers.containers_util import (
    ContainerInsertOrUpdateData,
    insert_or_update_container,
)
from backend.modules.hosts.hosts_model import HostsModel
from backend.modules.images.image_digest_util import (
    cache_available_image_metadata,
)
from backend.modules.settings.settings_enum import ESettingKey
from backend.modules.settings.settings_storage import SettingsStorage
from backend.util.get_version_from_labels import get_version_from_labels
from backend.util.jitter import jitter
from backend.util.now import now
from shared.runtime.runtime_models import (
    ContainerInspectResult,
    ImageInspectResult,
)
from shared.schemas.image_schemas import (
    InspectImageRequestBodySchema,
    PullImageRequestBodySchema,
)


async def run_check_container_job(
    client: AgentClient,
    host: HostsModel,
    container: ContainerInspectResult,
    tracker: HostJobTracker | None = None,
) -> ContainerJobResult:
    """
    Check if there is new image for the container.
    This func should not raise exceptions.
    """
    result: Final = ContainerJobResult(container)
    delay: Final = SettingsStorage.get(ESettingKey.REGISTRY_REQ_DELAY)
    name: Final = str(container.name)
    logger: Final = logging.getLogger(f"run_check_container_job.{container.name}")

    def _slot(
        status: EJobStatus, slot_result: ContainerJobResult | None = None
    ) -> None:
        if tracker:
            tracker.set_container(name, status, slot_result)

    async with async_session_maker() as session:
        try:
            logger.info("Checking container update availability")
            _slot(EJobStatus.PREPARING)

            image_spec: Final = get_container_image_spec(container)
            if not image_spec:
                logger.warning("Missing image spec. Exiting.")
                _slot(EJobStatus.DONE, result)
                return result
            logger.info(f"Image_spec is {image_spec}")

            result.image_spec = image_spec
            image_id: Final = container.image
            local_image: ImageInspectResult
            if image_id:
                local_image = await client.image.inspect(
                    InspectImageRequestBodySchema(spec_or_id=image_id)
                )
            else:
                local_image = await client.image.inspect(
                    InspectImageRequestBodySchema(spec_or_id=image_spec)
                )
            result.local_image = local_image

            local_digests: Final[list[str]] = list(local_image.repo_digests or [])
            result.local_digests = local_digests
            logger.info(f"Local digests is {local_digests}")

            c_db: Final = (
                await session.execute(
                    select(ContainersModel)
                    .where(
                        ContainersModel.host_id == host.id,
                        ContainersModel.name == container.name,
                    )
                    .limit(1)
                )
            ).scalar_one_or_none()

            _slot(EJobStatus.CHECKING)

            # pull image before digests
            # https://github.com/Quenary/tugtainer/issues/114
            if not image_is_local_build(local_image) and SettingsStorage.get(
                ESettingKey.PULL_BEFORE_CHECK
            ):
                logger.info("Pulling image before remote digests")
                remote_image: Final = await client.image.pull(
                    PullImageRequestBodySchema(image=image_spec)
                )
                result.remote_image = remote_image
                await asyncio.sleep(jitter(delay))

            remote_digests, update_known = await assess_image_update(
                image_spec, local_image, local_digests
            )
            result.remote_digests = remote_digests
            logger.info(f"Remote digests is {remote_digests}")
            result.current_version = get_version_from_labels(
                local_image.config.labels if local_image.config else None
            )

            result_lit: ContainerJobOutcome
            update_available: bool
            if update_known is None:
                # Failed lookup must not be reported as "up to date"
                logger.warning(
                    "No registry comparison; skipping availability conclusion"
                )
                result_lit = None
                update_available = bool(c_db.update_available) if c_db else False
            elif update_known:
                if c_db and c_db.remote_digests == remote_digests:
                    result_lit = "available(notified)"
                else:
                    result_lit = "available"
                update_available = True
            else:
                result_lit = "not_available"
                update_available = False
            logger.info(f"Check result is {result_lit}")
            result.result = result_lit

            if update_available and remote_digests:
                meta = await cache_available_image_metadata(
                    session,
                    image_spec,
                    remote_digests[0],
                    pulled_image=result.remote_image,
                    local_image=local_image,
                )
                if meta:
                    result.available_version = meta.version
                    result.available_created = meta.created

            result_db: Final[ContainerInsertOrUpdateData] = {
                "update_available": update_available,
                "checked_at": now(),
                "local_digests": local_digests,
                "remote_digests": remote_digests,
                "image_id": str(image_id),
            }
            # Record when remote digests last changed; never clear this field.
            if result_lit is not None and (
                not c_db or c_db.remote_digests != remote_digests
            ):
                result_db["remote_digests_changed_at"] = now()
            await insert_or_update_container(
                session, host.id, str(container.name), result_db
            )

            _slot(EJobStatus.DONE, result)
            return result
        except Exception:
            logger.exception("Failed to check container")
            _slot(EJobStatus.ERROR, result)
            return result
