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
    get_digests_for_platform,
)
from backend.modules.hosts.hosts_model import HostsModel
from backend.modules.settings.settings_enum import ESettingKey
from backend.modules.settings.settings_storage import SettingsStorage
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

            architecture = local_image.architecture
            os = local_image.os
            if not architecture:
                logging.warning(
                    f"{container.name} - Image missing 'architecture', exiting."
                )
                CACHE.update({"status": EActionStatus.DONE})
                return result
            if not os:
                logging.warning(
                    f"{container.name} - Image missing 'os', exiting."
                )
                CACHE.update({"status": EActionStatus.DONE})
                return result

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

            local_digests: list[str] = (
                c_db.local_digests
                if c_db and c_db.local_digests
                else []
            )
            stored_image_id = c_db.image_id if c_db else None

            logging.debug(
                f"{container.name} - actual image id: {image_id}"
            )
            logging.debug(
                f"{container.name} - stored image id: {stored_image_id}"
            )

            CACHE.update({"status": EActionStatus.CHECKING})
            # get local digests if missing
            # or if stored image_id does not match current
            if (
                not local_digests
                or not stored_image_id
                or stored_image_id != image_id
            ):
                for digest in local_image.repo_digests:
                    local_manifest = await client.manifest.inspect(
                        digest
                    )
                    logging.debug(
                        f"{container.name} - local manifest:\n{local_manifest}"
                    )

                    local_digests = get_digests_for_platform(
                        local_manifest,
                        architecture,
                        os,
                        str(local_image.id),
                    )
                    await asyncio.sleep(DELAY)
                    if local_digests:
                        break

            result.local_digests = local_digests
            logging.info(
                f"{container.name} - local digests for platform: {local_digests}"
            )

            # pull image before remote manifests
            # https://github.com/Quenary/tugtainer/issues/114
            if SettingsStorage.get(ESettingKey.PULL_BEFORE_CHECK):
                logging.info(
                    f"{container.name} - pulling image before remote manifest request"
                )
                remote_image = await client.image.pull(
                    PullImageRequestBodySchema(image=image_spec)
                )
                result.remote_image = remote_image
                await asyncio.sleep(DELAY)

            # get remote digests
            remote_manifest = await client.manifest.inspect(
                image_spec
            )
            logging.debug(
                f"{container.name} - remote manifest:\n{remote_manifest}"
            )
            remote_digests = get_digests_for_platform(
                remote_manifest,
                architecture,
                os,
                str(local_image.id),
            )
            result.remote_digests = remote_digests
            logging.info(
                f"{container.name} - remote digests for platform: {remote_digests}"
            )

            result_lit: ContainerCheckResultType = "not_available"
            if remote_digests and remote_digests != local_digests:
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
