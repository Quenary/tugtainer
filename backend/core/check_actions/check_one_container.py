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

from backend.core.action_result import (
    ContainerActionResult,
    ContainerCheckResultType,
)
from backend.core.agent_client import AgentClient
from backend.core.check_actions.check_actions_util import (
    get_image_remote_digest,
)
from backend.core.container_util.get_container_image_spec import (
    get_container_image_spec,
)
from backend.core.progress.progress_cache import ProgressCache
from backend.core.progress.progress_schemas import (
    ContainerActionProgress,
)
from backend.core.progress.progress_util import (
    get_container_cache_key,
    is_allowed_start_cache,
)
from backend.db.session import async_session_maker
from backend.enums.action_status_enum import EActionStatus
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


async def check_one_container(
    client: AgentClient,
    host: HostsModel,
    container: ContainerInspectResult,
) -> ContainerActionResult:
    """
    Check if there is new image for the container.
    This func should not raise exceptions.
    """
    result: Final = ContainerActionResult(container)
    delay: Final = SettingsStorage.get(ESettingKey.REGISTRY_REQ_DELAY)
    cache_key: Final = get_container_cache_key(
        host,
        container,
    )
    cache: Final = ProgressCache[ContainerActionProgress](cache_key)
    state: Final = cache.get()
    logger: Final = logging.getLogger(f"check_one_container.{container.name}")

    if not is_allowed_start_cache(state):
        logger.warning("Check action already running. Exiting.")
        return result

    async with async_session_maker() as session:
        try:
            logger.info("Checking container update availability")
            cache.set({"status": EActionStatus.PREPARING})

            image_spec: Final = get_container_image_spec(container)
            if not image_spec:
                logger.warning("Missing image spec. Exiting.")
                cache.update({"status": EActionStatus.DONE})
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
                cache.update({"status": EActionStatus.DONE})
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

            cache.update({"status": EActionStatus.CHECKING})

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

            result_lit: ContainerCheckResultType = "not_available"
            # check if any remote digest missing in local_digests
            if any(all(rd not in ld for ld in local_digests) for rd in remote_digests):
                if c_db and c_db.remote_digests == remote_digests:
                    result_lit = "available(notified)"
                else:
                    result_lit = "available"
            logger.info(f"Check result is {result_lit}")
            result.result = result_lit

            result_db: Final[ContainerInsertOrUpdateData] = {
                "update_available": result_lit != "not_available",
                "checked_at": now(),
                "local_digests": local_digests,
                "remote_digests": remote_digests,
                "image_id": str(image_id),
            }
            await insert_or_update_container(
                session, host.id, str(container.name), result_db
            )

            cache.update({"status": EActionStatus.DONE, "result": result})
            return result
        except Exception:
            logger.exception("Failed to check container")
            cache.update({"status": EActionStatus.ERROR, "result": result})
            return result
