import asyncio
import logging
from typing import Final

from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from python_on_whales.components.image.models import (
    ImageInspectResult,
)
from sqlalchemy import select

from backend.core.agent_client import AgentClient
from backend.core.container_util.get_container_image_spec import (
    get_container_image_spec,
)
from backend.core.jobs.check.check_util import (
    get_image_remote_digest,
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
from backend.modules.settings.settings_enum import ESettingKey
from backend.modules.settings.settings_storage import SettingsStorage
from backend.util.jitter import jitter
from backend.util.now import now
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

            if not local_image.repo_digests:
                logger.warning(
                    "Missing repo digests. Presumably a local image. Exiting."
                )
                _slot(EJobStatus.DONE, result)
                return result

            local_digests: Final = local_image.repo_digests
            result.local_digests = local_image.repo_digests
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
            if SettingsStorage.get(ESettingKey.PULL_BEFORE_CHECK):
                logger.info("Pulling image before remote digests")
                remote_image: Final = await client.image.pull(
                    PullImageRequestBodySchema(image=image_spec)
                )
                result.remote_image = remote_image
                await asyncio.sleep(jitter(delay))

            # get remote digests
            remote_digests: list[str] = []
            for d in local_digests:
                try:
                    rd = await get_image_remote_digest(image_spec, d)
                    if rd:
                        remote_digests = [rd]
                        break
                except Exception:
                    logger.exception(
                        f"Failed to get remote digest for {image_spec} {d}"
                    )
                finally:
                    await asyncio.sleep(jitter(delay))

            result.remote_digests = remote_digests
            logger.info(f"Remote digests is {remote_digests}")

            result_lit: ContainerJobOutcome
            update_available: bool
            if not remote_digests:
                # Failed lookup must not be reported as "up to date"
                logger.warning(
                    "No remote digests obtained; skipping availability conclusion"
                )
                result_lit = None
                update_available = bool(c_db.update_available) if c_db else False
            elif any(
                all(rd not in ld for ld in local_digests)
                for rd in remote_digests
            ):
                # Remote digest missing from local digests → update available
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
