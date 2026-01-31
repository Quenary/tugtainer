from python_on_whales.components.buildx.imagetools.models import (
    ImageVariantManifest,
)
from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from python_on_whales.components.image.models import (
    ImageInspectResult,
)
import logging
from typing import cast
from sqlalchemy import select
import asyncio
from backend.db.session import async_session_maker
from backend.db.models import ContainersModel, HostsModel
from backend.core.container.schemas.check_result import (
    CheckContainerUpdateAvailableResult,
    ContainerCheckResult,
    ContainerCheckResultType,
    GroupCheckResult,
    HostCheckResult,
)
from backend.core import HostsManager
from backend.core.notifications_core import send_check_notification
from backend.db.util import insert_or_update_container
from backend.db.util.insert_or_update_container import (
    ContainerInsertOrUpdateData,
)
from backend.enums.check_status_enum import ECheckStatus
from backend.core.container.util import (
    get_container_image_spec,
    wait_for_container_healthy,
    get_container_config,
    merge_container_config_with_image,
    update_containers_data_after_check,
    is_running_container,
    get_digests_for_platform,
)
from backend.core.container import (
    GroupCheckProgressCache,
    HostCheckProgressCache,
    AllCheckProgressCache,
    ProcessCache,
    ALL_CONTAINERS_STATUS_KEY,
    get_host_cache_key,
    get_group_cache_key,
)
from backend.core.container.container_group import (
    ContainerGroupItem,
    get_containers_groups,
    ContainerGroup,
)
from backend.core.agent_client import AgentClient
from backend.exception import TugAgentClientError
from backend.helpers.now import now
from shared.schemas.command_schemas import RunCommandRequestBodySchema
from shared.schemas.container_schemas import (
    CreateContainerRequestBodySchema,
    GetContainerListBodySchema,
)
from shared.schemas.image_schemas import (
    InspectImageRequestBodySchema,
    PruneImagesRequestBodySchema,
    PullImageRequestBodySchema,
    TagImageRequestBodySchema,
)
from backend.const import TUGTAINER_PROTECTED_LABEL

# Allowed cache statuses for further processing
_ALLOW_STATUSES = [ECheckStatus.DONE, ECheckStatus.ERROR]


async def check_container_update_available(
    host_id: int,
    client: AgentClient,
    container: ContainerInspectResult,
) -> CheckContainerUpdateAvailableResult:
    """
    Check if there is new image for the container.
    This func should not raise exceptions.
    """
    logging.info(
        f"{container.name} - Checking container update availability."
    )
    result = CheckContainerUpdateAvailableResult()
    async with async_session_maker() as session:
        try:
            image_spec = get_container_image_spec(container)
            if not image_spec:
                logging.warning(
                    f"{container.name} - Cannot proceed, no image spec."
                )
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
                return result

            architecture = local_image.architecture
            os = local_image.os
            if not architecture:
                logging.warning(
                    f"{container.name} - Image missing 'architecture', exiting."
                )
                return result
            if not os:
                logging.warning(
                    f"{container.name} - Image missing 'os', exiting."
                )
                return result

            stmt = (
                select(ContainersModel)
                .where(
                    ContainersModel.host_id == host_id,
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
                    if local_digests:
                        break

            result.local_digests = local_digests
            logging.info(
                f"{container.name} - local digests for platform: {local_digests}"
            )

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

            is_available: ContainerCheckResultType = (
                "available"
                if remote_digests and remote_digests != local_digests
                else "not_available"
            )

            result_db: ContainerInsertOrUpdateData = {
                "checked_at": now(),
                "local_digests": local_digests,
                "image_id": str(image_id),
            }

            if is_available == "available":
                if c_db and c_db.remote_digests == remote_digests:
                    logging.debug(
                        f"{container.name} - Marked as available(notified)"
                    )
                    is_available = "available(notified)"
                else:
                    result_db["remote_digests"] = remote_digests

            logging.info(
                f"{container.name} - Check result is {is_available}"
            )
            result.result = is_available
            c_db = await insert_or_update_container(
                session, host_id, str(container.name), result_db
            )
            return result
        except TugAgentClientError as e:
            if e.status == 404:
                logging.error(
                    "Make sure the Tugtainer Agent is up to date"
                )
            await session.commit()
            return result
        except Exception as e:
            logging.exception(e)
            await session.commit()
            return result


async def check_group(
    client: AgentClient,
    host: HostsModel,
    group: ContainerGroup,
    update: bool,
) -> GroupCheckResult | None:
    """
    Check (and update) group of containers.
    :param client: docker client
    :param host: docker host
    :param group: group to be checked/updated
    :param update: update flag (only check if False)
    """
    logging.info(
        f"""
=================================================================
Starting check of group: '{group.name}', containers count: {len(group.containers)}"""
    )
    STATUS_KEY = get_group_cache_key(host, group)
    CACHE = ProcessCache[GroupCheckProgressCache](STATUS_KEY)
    STATUS = CACHE.get()
    if STATUS and STATUS.get("status") not in _ALLOW_STATUSES:
        logging.warning(
            f"Check process of {STATUS_KEY} is already running."
        )
        return None
    CACHE.set({"status": ECheckStatus.PREPARING})
    for_check = [
        item
        for item in group.containers
        if item.action in ["check", "update"]
    ]
    CACHE.update({"status": ECheckStatus.CHECKING})
    for gc in for_check:
        res = await check_container_update_available(
            host.id, client, gc.container
        )
        gc.temp_result = res.result
        gc.image_spec = res.image_spec
        gc.local_image = res.local_image
        gc.local_digests = res.local_digests
        gc.local_digests = res.remote_digests

    # region Helper functions
    def _will_update(gc: ContainerGroupItem) -> bool:
        """Whether to update container"""
        return bool(
            gc.temp_result in ["available", "available(notified)"]
            and gc.action == "update"
            and not gc.protected
            and is_running_container(gc.container)
        )

    def _will_skip(gc: ContainerGroupItem) -> bool:
        """Whether to skip container"""
        if gc.protected:
            logging.info(
                f"Container {gc.name} labeled with {TUGTAINER_PROTECTED_LABEL}, skipping."
            )
            return True
        elif not is_running_container(gc.container):
            logging.info(
                f"Container {gc.name} is not running, skipping."
            )
            return True
        return False

    def _group_state_to_result(
        group: ContainerGroup,
    ) -> GroupCheckResult:
        return GroupCheckResult(
            host_id=host.id,
            host_name=host.name,
            items=[
                ContainerCheckResult(
                    container=item.container,
                    local_image=item.local_image,
                    remote_image=item.remote_image,
                    local_digests=item.local_digests,
                    remote_digests=item.remote_digests,
                    result=item.temp_result,
                )
                for item in group.containers
            ],
        )

    async def _on_stop_fail():
        """If failed to stop containers before updating"""
        for gc in group.containers:
            await client.container.start(gc.name)
        result = _group_state_to_result(group)
        await update_containers_data_after_check(result)
        CACHE.update({"status": ECheckStatus.ERROR, "result": result})
        return result

    async def _run_commands(commands: list[list[str]]):
        """Run commands after container started"""
        for c in commands:
            try:
                logging.info(f"Running command: {c}")
                out, err = await client.command.run(
                    RunCommandRequestBodySchema(command=c)
                )
                if out:
                    logging.info(out)
                if err:
                    logging.error(err)
            except Exception as e:
                logging.exception(e)
                logging.error(f"Error while running command {c}")

    # endregion

    any_for_update: bool = any(
        _will_update(item) for item in group.containers
    )
    if not update or not any_for_update:
        result = _group_state_to_result(group)
        await update_containers_data_after_check(result)
        logging.info(
            f"""Group check completed. 
================================================================="""
        )
        CACHE.update({"status": ECheckStatus.DONE, "result": result})
        return result

    logging.info("Starting to update a group...")
    CACHE.update({"status": ECheckStatus.UPDATING})

    # Pulling images for updatable containers
    for gc in group.containers:
        if _will_update(gc):
            try:
                logging.info(
                    f"Pulling image for container {gc.container.name}, spec {gc.image_spec}..."
                )
                remote_image = await client.image.pull(
                    PullImageRequestBodySchema(
                        image=cast(str, gc.image_spec)
                    )
                )
                gc.remote_image = remote_image
            except Exception as e:
                logging.exception(e)
                logging.error(
                    f"""Failed to pull the image for container {gc.container.name} with spec {gc.image_spec}
================================================================="""
                )
                result = _group_state_to_result(group)
                await update_containers_data_after_check(result)
                CACHE.update(
                    {"status": ECheckStatus.ERROR, "result": result}
                )
                return result

    # Getting containers configs and stopping them,
    # from most dependent to most dependable.
    for gc in group.containers[::-1]:
        if _will_skip(gc):
            continue
        try:
            logging.info(
                f"Getting config for container {gc.container.name}..."
            )
            config, commands = get_container_config(gc.container)
            gc.config = config
            gc.commands = commands
        except Exception as e:
            logging.exception(e)
            if _will_update(gc):
                logging.error(
                    """Failed to get config for updatable container. Exiting group update.
================================================================="""
                )
                return await _on_stop_fail()
        try:
            logging.info(f"Stopping container {gc.container.name}...")
            await client.container.stop(gc.name)
        except Exception as e:
            logging.exception(e)
            logging.error(
                """Failed to stop container. Exiting group update.
================================================================="""
            )
            return await _on_stop_fail()

    # Updating and/or starting containers,
    # from most dependable to most dependent.

    # Indicates was there an exception during the update
    # If True, the following updates will not be processed.
    any_failed: bool = False

    for gc in group.containers:
        if _will_skip(gc):
            continue
        c_name = gc.name
        # Updating container
        if _will_update(gc) and not any_failed:
            image_spec = cast(str, gc.image_spec)
            local_image = cast(ImageInspectResult, gc.local_image)
            remote_image = cast(ImageInspectResult, gc.remote_image)
            config = cast(CreateContainerRequestBodySchema, gc.config)
            logging.info(f"Starting update of container {c_name}...")
            try:
                logging.info("Removing container...")
                await client.container.remove(c_name)
                logging.info("Merging configs...")
                merged_config = merge_container_config_with_image(
                    config, remote_image
                )
                logging.info("Recreating container...")
                new_c = await client.container.create(merged_config)
                logging.info("Starting container...")
                await client.container.start(c_name)
                await _run_commands(gc.commands)
                logging.info("Waiting for healthchecks...")
                if await wait_for_container_healthy(
                    client, new_c, host.container_hc_timeout
                ):
                    logging.info("Container is healthy!")
                    gc.container = new_c
                    gc.temp_result = "updated"
                    continue
                # Failed healthchecks
                logging.warning(
                    "Container is unhealthy, rolling back..."
                )
                await client.container.stop(c_name)
                await client.container.remove(c_name)
            except Exception as e:
                logging.exception(e)
                logging.error("Update failed, rolling back...")
                # Try to remove possibly existing container
                try:
                    if await client.container.exists(c_name):
                        logging.warning(
                            "Removing failed container..."
                        )
                        await client.container.stop(c_name)
                        await client.container.remove(c_name)
                except:
                    pass
            # Rolling back
            try:
                logging.warning("Tagging previous image...")
                await client.image.tag(
                    TagImageRequestBodySchema(
                        spec_or_id=str(local_image.id),
                        tag=image_spec,
                    )
                )
                logging.warning(
                    "Creating container with previous image..."
                )
                rolled_back = await client.container.create(config)
                logging.warning("Starting container...")
                await client.container.start(str(rolled_back.id))
                await _run_commands(gc.commands)
                gc.container = rolled_back
                gc.temp_result = "rolled_back"
                logging.warning("Waiting for healthchecks...")
                if await wait_for_container_healthy(
                    client, rolled_back, host.container_hc_timeout
                ):
                    logging.warning(
                        "Container is healthy after rolling back!"
                    )
                    continue
                logging.warning(
                    "Container is unhealthy after rolling back!"
                )
            # Failed to roll back
            except Exception as e:
                logging.exception(e)
                logging.error("Failed to roll back container!")
                gc.temp_result = "failed"
                any_failed = True
        # Start not updatable container
        else:
            try:
                logging.info(
                    f"Starting non-updatable container {gc.container.name}"
                )
                await client.container.start(gc.name)
                await _run_commands(gc.commands)
                logging.info("Waiting for healthchecks...")
                if await wait_for_container_healthy(
                    client, gc.container, host.container_hc_timeout
                ):
                    logging.info("Container is healthy!")
                    continue
                logging.warning("Container is unhealthy! Continue...")
                continue
            except Exception as e:
                logging.exception(e)
                logging.warning(
                    "Failed to start non-updatable container. Continue..."
                )
    result = _group_state_to_result(group)
    await update_containers_data_after_check(result)
    logging.info(
        f"""Group update completed.
================================================================="""
    )
    CACHE.update({"status": ECheckStatus.DONE, "result": result})
    return result


async def check_host(
    host: HostsModel,
    client: AgentClient,
    update: bool,
    containers_db: list[ContainersModel],
) -> HostCheckResult | None:
    """
    Check (and update) containers of specified host.
    :param host: host info from db
    :param client: host's docker client
    :param update: update flag (only check if False)
    :param containers_db: containers db data
    """
    result = HostCheckResult(host_id=host.id, host_name=host.name)
    STATUS_KEY = get_host_cache_key(host)
    CACHE = ProcessCache[HostCheckProgressCache](STATUS_KEY)
    try:
        STATUS = CACHE.get()
        if STATUS and STATUS.get("status") not in _ALLOW_STATUSES:
            logging.warning(
                f"Check process for {STATUS_KEY} is already running."
            )
            return None

        CACHE.set(
            {"status": ECheckStatus.PREPARING},
        )
        logging.info(f"Starting check for host '{host.name}'")

        containers: list[ContainerInspectResult] = (
            await client.container.list(
                GetContainerListBodySchema(all=True)
            )
        )
        groups = get_containers_groups(containers, containers_db)
        CACHE.update(
            {
                "status": (
                    ECheckStatus.UPDATING
                    if update
                    else ECheckStatus.CHECKING
                )
            },
        )

        for group in groups.values():
            res = await check_group(client, host, group, update)
            if res:
                result.items.extend(res.items)

        if host.prune:
            CACHE.update({"status": ECheckStatus.PRUNING})
            logging.info(f"Pruning images on host '{host.name}'")
            try:
                result.prune_result = await client.image.prune(
                    PruneImagesRequestBodySchema(all=host.prune_all)
                )
            except Exception as e:
                logging.exception(e)
                logging.error(
                    f"Failed to prune images on host '{host.name}'"
                )

        CACHE.update({"status": ECheckStatus.DONE, "result": result})
        return result
    except Exception as e:
        CACHE.update(
            {"status": ECheckStatus.ERROR},
        )
        logging.exception(e)
        logging.error(f"Failed to check host {host.name}")
        return None


async def check_all(update: bool):
    """
    Main func for scheduled/manual check/update all containers
    marked for it, for all specified docker hosts.
    Function performs checks in separate threads for each host.
    Should not raises errors, only logging.
    """
    CACHE = ProcessCache[AllCheckProgressCache](
        ALL_CONTAINERS_STATUS_KEY
    )
    try:
        STATUS = CACHE.get()
        if STATUS and STATUS.get("status") not in _ALLOW_STATUSES:
            logging.warning(
                "General check process is already running."
            )
            return

        CACHE.set(
            {"status": ECheckStatus.PREPARING},
        )
        logging.info("Start checking of all containers for all hosts")

        async with async_session_maker() as session:
            result = await session.execute(
                select(HostsModel).where(HostsModel.enabled == True)
            )
            hosts = result.scalars().all()
            host_containers_db: dict[int, list[ContainersModel]] = {}
            for h in hosts:
                result = await session.execute(
                    select(ContainersModel).where(
                        ContainersModel.host_id == h.id
                    )
                )
                host_containers_db[h.id] = list(
                    result.scalars().all()
                )

        tasks: list[asyncio.Future[HostCheckResult | None]] = []
        for h in hosts:
            cli = HostsManager.get_host_client(h)
            cor = check_host(
                h,
                cli,
                update,
                host_containers_db.get(h.id, []),
            )
            t = asyncio.create_task(cor)
            tasks.append(t)

        CACHE.update(
            {
                "status": (
                    ECheckStatus.UPDATING
                    if update
                    else ECheckStatus.CHECKING
                )
            }
        )
        results = await asyncio.gather(*tasks)

        CACHE.update(
            {
                "status": ECheckStatus.DONE,
                "result": {
                    item.host_id: item for item in results if item
                },
            }
        )

        # filter undefined results
        results = [item for item in results if item]
        await send_check_notification(results)

    except Exception as e:
        CACHE.update({"status": ECheckStatus.ERROR})
        logging.exception(e)
        logging.error(
            "Error while checking of all containers for all hosts"
        )
