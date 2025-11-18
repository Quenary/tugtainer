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
    GroupCheckResult,
    HostCheckResult,
    ShrinkedContainer,
)
from backend.core import HostsManager
from backend.core.notifications_core import send_notification
from backend.enums.check_status_enum import ECheckStatus
from backend.config import Config
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


def _get_shrinked_containers(
    containers: list[ContainerInspectResult],
) -> list[ShrinkedContainer]:
    return [ShrinkedContainer.from_c(c) for c in containers]


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
    result = GroupCheckResult(host_id=host.id, host_name=host.name)
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
        gc.available = res.available
        gc.image_spec = res.image_spec
        gc.old_image = res.old_image
        gc.new_image = res.new_image
    result.not_available = _get_shrinked_containers(
        [
            item.container
            for item in group.containers
            if not item.available
        ]
    )

    # region Helper functions
    def will_update(gc: ContainerGroupItem) -> bool:
        """Whether to update container"""
        return bool(
            gc.available
            and gc.image_spec
            and gc.old_image
            and gc.new_image
            and gc.action == "update"
            and not gc.protected
        )

    async def on_stop_fail():
        """If failed to stop containers before updating"""
        for gc in group.containers:
            await client.container.start(gc.name)
        result.available = _get_shrinked_containers(
            [
                item.container
                for item in group.containers
                if item.available
            ]
        )
        await update_containers_data_after_check(result)
        CACHE.update({"status": ECheckStatus.ERROR})
        return result

    async def run_commands(commands: list[list[str]]):
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

    any_for_update: bool = bool(
        len([item for item in group.containers if will_update(item)])
        > 0
    )
    if not update or not any_for_update:
        result.available = _get_shrinked_containers(
            [
                item.container
                for item in group.containers
                if item.available
            ]
        )
        await update_containers_data_after_check(result)
        logging.info(
            f"""Group check completed.
================================================================="""
        )
        CACHE.update({"status": ECheckStatus.DONE})
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
            if will_update(gc):
                logging.error(
                    """Failed to get config for updatable container. Exiting group update.
================================================================="""
                )
                return await on_stop_fail()
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
            return await on_stop_fail()

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
        if will_update(gc) and not any_failed:
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
                await run_commands(gc.commands)
                logging.info("Waiting for healthchecks...")
                if await wait_for_container_healthy(client, new_c):
                    logging.info("Container is healthy!")
                    gc.container = new_c
                    gc.available = False
                    result.updated.append(
                        ShrinkedContainer.from_c(new_c)
                    )
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
                if client.container.exists(c_name):
                    logging.warning("Removing failed container...")
                    await client.container.stop(c_name)
                    await client.container.remove(c_name)
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
                await run_commands(gc.commands)
                gc.container = rolled_back
                result.rolled_back.append(
                    ShrinkedContainer.from_c(rolled_back)
                )
                logging.warning("Waiting for healthchecks...")
                if await wait_for_container_healthy(
                    client, rolled_back
                ):
                    logging.warning("Container is healthy!")
                    continue
                logging.warning("Container is unhealthy!")
            # Failed to roll back
            except Exception as e:
                logging.exception(e)
                logging.error("Failed to roll back container!")
                result.failed.append(
                    ShrinkedContainer.from_c(gc.container)
                )
                any_failed = True
        # Start not updatable container
        else:
            try:
                logging.info(
                    f"Starting non-updatable container {gc.container.name}"
                )
                await client.container.start(gc.name)
                await run_commands(gc.commands)
                logging.info("Waiting for healthchecks...")
                if await wait_for_container_healthy(
                    client, gc.container
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
    result.available = _get_shrinked_containers(
        [
            item.container
            for item in group.containers
            if item.available
        ]
    )
    await update_containers_data_after_check(result)
    logging.info(
        f"""Group update completed.
================================================================="""
    )
    CACHE.update({"status": ECheckStatus.DONE})
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

        for _, group in groups.items():
            res = await check_group(client, host, group, update)
            if res:
                result.not_available.extend(res.not_available)
                result.available.extend(res.available)
                result.updated.extend(res.updated)
                result.rolled_back.extend(res.rolled_back)
                result.failed.extend(res.failed)

        CACHE.update(
            {
                "available": len(result.available),
                "updated": len(result.updated),
                "rolled_back": len(result.rolled_back),
                "failed": len(result.failed),
            },
        )

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

        CACHE.update({"status": ECheckStatus.DONE})
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

        CACHE.update({"status": ECheckStatus.DONE})
        await _send_notification(results)
    except Exception as e:
        CACHE.update({"status": ECheckStatus.ERROR})
        logging.exception(e)
        logging.error(
            "Error while checking of all containers for all hosts"
        )


async def _send_notification(results: list[HostCheckResult | None]):
    """
    Send notification with general check results
    """

    def get_cont_str(c: ShrinkedContainer) -> str:
        return f"- {c.name} {c.image_spec}\n"

    body: str = ""
    for res in results:
        if not res:
            continue
        host_part: str = ""
        if res.updated:
            host_part += "### *Updated*:\n"
            for c in res.updated:
                host_part += get_cont_str(c)
        if res.available:
            host_part += "### *Available*:\n"
            for c in res.available:
                host_part += get_cont_str(c)
        if res.rolled_back:
            host_part += "### *Rolled-back after fail*:\n"
            for c in res.rolled_back:
                host_part += get_cont_str(c)
        if res.failed:
            host_part += f"### *Failed and not rolled-back*:\n"
            for c in res.failed:
                host_part += get_cont_str(c)
        if res.prune_res:
            host_part += f"{res.prune_res}"
        if host_part:
            body += f"\n## Host: {res.host_name}\n" + host_part
    if body:
        body = f"# Tugtainer ({Config.HOSTNAME})\n" + body
    try:
        if body:
            await send_notification(body=body)
    except Exception as e:
        logging.exception(e)
        logging.error("Failed to send notification")
