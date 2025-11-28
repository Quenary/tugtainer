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
    GroupCheckResult,
    HostCheckResult,
)
from backend.core import HostsManager
from backend.core.notifications_core import send_check_notification
from backend.enums.check_status_enum import ECheckStatus
from backend.core.container.util import (
    get_container_image_spec,
    get_container_image_id,
    wait_for_container_healthy,
    get_container_config,
    merge_container_config_with_image,
    update_containers_data_after_check,
)
from backend.core.container import (
    GroupCheckData,
    HostCheckData,
    AllCheckData,
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
    client: AgentClient,
    container: ContainerInspectResult,
) -> CheckContainerUpdateAvailableResult:
    """
    Check if there is new image for the container.
    This func should not raise exceptions.
    """
    logging.info(
        f"Checking container '{container.name}' update availability."
    )
    result = CheckContainerUpdateAvailableResult()
    try:
        image_spec = get_container_image_spec(container)
        if not image_spec:
            logging.warning(f"Cannot proceed, no image spec.")
            return result
        result.image_spec = image_spec
        image_id = get_container_image_id(container)
        old_image: ImageInspectResult
        if image_id:
            old_image = await client.image.inspect(
                InspectImageRequestBodySchema(spec_or_id=image_id)
            )
        else:
            old_image = await client.image.inspect(
                InspectImageRequestBodySchema(spec_or_id=image_spec)
            )
        result.old_image = old_image
        if not old_image.repo_digests:
            logging.warning(
                f"Image missing repo digests. Presumably a local image."
            )
            return result
        new_image = await client.image.pull(
            PullImageRequestBodySchema(image=image_spec)
        )
        if not isinstance(new_image, ImageInspectResult):
            logging.warning(f"Failed to pull new image.'")
            return result
        result.new_image = new_image
        available: bool = bool(
            old_image
            and new_image
            and old_image.repo_digests != new_image.repo_digests
        )
        result.available = available
        if available:
            logging.info(f"New image found!")
        else:
            logging.info(f"No new image found.")
        return result
    except Exception as e:
        logging.exception(e)
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
    CACHE = ProcessCache[GroupCheckData](STATUS_KEY)
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
            client, gc.container
        )
        gc.temp_result = (
            "available" if res.available else "not_available"
        )
        gc.image_spec = res.image_spec
        gc.old_image = res.old_image
        gc.new_image = res.new_image

    # region Helper functions
    def _will_update(gc: ContainerGroupItem) -> bool:
        """Whether to update container"""
        return bool(
            gc.temp_result == "available"
            and gc.image_spec
            and gc.old_image
            and gc.new_image
            and gc.action == "update"
            and not gc.protected
        )

    def _group_state_to_result(
        group: ContainerGroup,
    ) -> GroupCheckResult:
        return GroupCheckResult(
            host_id=host.id,
            host_name=host.name,
            items=[
                ContainerCheckResult(
                    container=item.container,
                    old_image=item.old_image,
                    new_image=item.new_image,
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

    protected_containers = [
        gc for gc in group.containers if gc.protected
    ]
    for gc in protected_containers:
        logging.info(
            f"Container {gc.name} labeled with {TUGTAINER_PROTECTED_LABEL} and will be skipped."
        )

    # Starting from most dependent
    for gc in group.containers[::-1]:
        # Skipping protected containers
        if gc.protected:
            continue
        # Getting configs for all containers
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
        # Stopping all containers
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

    # Starting from most dependable.
    # At that moment all containers should be stopped.
    # Will update/start them in dependency order

    # Indicates was there an exception during the update
    # If True, the following updates will not be processed.
    any_failed: bool = False

    for gc in group.containers:
        # Skipping protected containers
        if gc.protected:
            continue
        c_name = gc.name
        # Updating container
        if _will_update(gc) and not any_failed:
            image_spec = cast(str, gc.image_spec)
            old_image = cast(ImageInspectResult, gc.old_image)
            new_image = cast(ImageInspectResult, gc.new_image)
            config = cast(CreateContainerRequestBodySchema, gc.config)
            logging.info(f"Starting update of container {c_name}...")
            try:
                logging.info("Removing container...")
                await client.container.remove(c_name)
                logging.info("Merging configs...")
                merged_config = merge_container_config_with_image(
                    config, new_image
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
                        spec_or_id=str(old_image.id),
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
                    logging.warning("Container is healthy!")
                    continue
                logging.warning("Container is unhealthy!")
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
    CACHE = ProcessCache[HostCheckData](STATUS_KEY)
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
                output = await client.image.prune(
                    PruneImagesRequestBodySchema(all=host.prune_all)
                )
                lines = [
                    line.strip()
                    for line in output.splitlines()
                    if line.strip()
                ]
                result.prune_res = lines[-1] if lines else None
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
    CACHE = ProcessCache[AllCheckData](ALL_CONTAINERS_STATUS_KEY)
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

        results = [item for item in results if item]
        await send_check_notification(results)
    except Exception as e:
        CACHE.update({"status": ECheckStatus.ERROR})
        logging.exception(e)
        logging.error(
            "Error while checking of all containers for all hosts"
        )
