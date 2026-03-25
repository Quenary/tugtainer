import asyncio
from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from python_on_whales.components.image.models import (
    ImageInspectResult,
)
import logging
from sqlalchemy import select
from backend.core.agent_client import AgentClient
from backend.core.check_actions.check_actions_util import (
    get_image_remote_digest,
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
from backend.core.action_result import (
    ContainerActionResult,
    ContainerCheckResultType,
)
from backend.modules.containers.containers_util import (
    insert_or_update_container,
    ContainerInsertOrUpdateData,
)
from backend.core.container_util import (
    get_container_image_spec,
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
    logging.info(
        f"{container.name} - Checking container update availability."
    )
    result = ContainerActionResult(container)
    DELAY = SettingsStorage.get(ESettingKey.REGISTRY_REQ_DELAY)
    CACHE_KEY = get_container_cache_key(
        host,
        container,
    )
    CACHE = ProgressCache[ContainerActionProgress](CACHE_KEY)
    async with async_session_maker() as session:
        try:
            STATE = CACHE.get()
            if not is_allowed_start_cache(STATE):
                logging.warning(
                    f"{container.name} - check action already running."
                )
                return result

            CACHE.set({"status": EActionStatus.PREPARING})
            image_spec = get_container_image_spec(container)
            if not image_spec:
                logging.warning(
                    f"{container.name} - Cannot proceed, no image spec."
                )
                CACHE.update({"status": EActionStatus.DONE})
                return result
            logging.info(f"{container.name} - image_spec: {image_spec}")

            result.image_spec = image_spec
            image_id = container.image
            local_image: ImageInspectResult
            if image_id:
                local_image = await client.image.inspect(
                    InspectImageRequestBodySchema(spec_or_id=image_id)
                )
            else:
                local_image = await client.image.inspect(
                    InspectImageRequestBodySchema(
                        spec_or_id=image_spec
                    )
                )
            result.local_image = local_image

            if not local_image.repo_digests:
                logging.warning(
                    f"{container.name} - Image missing repo digests. Presumably a local image."
                )
                CACHE.update({"status": EActionStatus.DONE})
                return result

            local_digests = local_image.repo_digests
            result.local_digests = local_image.repo_digests
            logging.info(
                f"{container.name} - local digests: {local_digests}"
            )

            stmt = (
                select(ContainersModel)
                .where(
                    ContainersModel.host_id == host.id,
                    ContainersModel.name == container.name,
                )
                .limit(1)
            )
            stmt_res = await session.execute(stmt)
            c_db = stmt_res.scalar_one_or_none()

            CACHE.update({"status": EActionStatus.CHECKING})

            # pull image before digests
            # https://github.com/Quenary/tugtainer/issues/114
            if SettingsStorage.get(ESettingKey.PULL_BEFORE_CHECK):
                logging.info(
                    f"{container.name} - pulling image before remote digests"
                )
                remote_image = await client.image.pull(
                    PullImageRequestBodySchema(image=image_spec)
                )
                result.remote_image = remote_image
                await asyncio.sleep(jitter(DELAY))

            # get remote digests
            remote_digests: list[str] = []
            for d in local_digests:
                try:
                    rd = await get_image_remote_digest(image_spec, d)
                    if rd:
                        remote_digests = [rd]
                        break
                    await asyncio.sleep(jitter(DELAY))
                except Exception as e:
                    logging.error(
                        f"{container.name} - failed to get remote digest for {image_spec} with local digest {d}"
                    )
                    logging.exception(e)
            result.remote_digests = remote_digests
            logging.info(
                f"{container.name} - Remote digests: {remote_digests}"
            )

            result_lit: ContainerCheckResultType = "not_available"
            # check if any remote digest missing in local_digests
            if any(
                all(rd not in ld for ld in local_digests)
                for rd in remote_digests
            ):
                if c_db and c_db.remote_digests == remote_digests:
                    result_lit = "available(notified)"
                else:
                    result_lit = "available"
            logging.info(
                f"{container.name} - Check result is {result_lit}"
            )
            result.result = result_lit

            result_db: ContainerInsertOrUpdateData = {
                "update_available": result_lit != "not_available",
                "checked_at": now(),
                "local_digests": local_digests,
                "remote_digests": remote_digests,
                "image_id": str(image_id),
            }
            await insert_or_update_container(
                session, host.id, str(container.name), result_db
            )

            CACHE.update(
                {"status": EActionStatus.DONE, "result": result}
            )
            return result
        except Exception as e:
            logging.exception(e)
            CACHE.update(
                {"status": EActionStatus.ERROR, "result": result}
            )
            return result
