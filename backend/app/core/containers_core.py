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
from concurrent.futures import ThreadPoolExecutor
from backend.app.db.session import async_session_maker
from backend.app.db.models import ContainersModel, HostsModel
from backend.app.core.container.util import (
    update_containers_data_after_check,
)
from backend.app.core.container.schemas.check_result import (
    CheckContainerUpdateAvailableResult,
    GroupCheckResult,
    HostCheckResult,
    ShrinkedContainer,
)
from backend.app.core import HostsManager
from backend.app.core.notifications_core import send_notification
from backend.app.enums.check_status_enum import ECheckStatus
from backend.app.config import Config
from backend.app.core.container.util import (
    get_container_image_spec,
    get_container_image_id,
    wait_for_container_healthy_sync,
    get_container_config,
    merge_container_config_with_image,
    update_containers_data_after_check,
)
from backend.app.core.container import (
    GroupCheckData,
    HostCheckData,
    AllCheckData,
    ProcessCache,
    ALL_CONTAINERS_STATUS_KEY,
    get_host_cache_key,
    get_group_cache_key,
)
from backend.app.core.container.container_group import (
    ContainerGroupItem,
    get_containers_groups,
    ContainerGroup,
)
from backend.app.core.agent_client import AgentClient
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

# Allowed cache statuses for further processing
_ALLOW_STATUSES = [ECheckStatus.DONE, ECheckStatus.ERROR]


def _get_shrinked_containers(
    containers: list[ContainerInspectResult],
) -> list[ShrinkedContainer]:
    return [ShrinkedContainer.from_c(c) for c in containers]


def check_container_update_available(
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
            old_image = client.image.inspect(
                InspectImageRequestBodySchema(spec_or_id=image_id)
            )
        else:
            old_image = client.image.inspect(
                InspectImageRequestBodySchema(spec_or_id=image_spec)
            )
        result.old_image = old_image
        if not old_image.repo_digests:
            logging.warning(
                f"Image missing repo digests. Presumably a local image."
            )
            return result
        new_image = client.image.pull(
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


def check_group(
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
        res = check_container_update_available(client, gc.container)
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
        )

    def on_stop_fail():
        """If failed to stop containers before updating"""
        for gc in group.containers:
            client.container.start(gc.name)
        result.available = _get_shrinked_containers(
            [
                item.container
                for item in group.containers
                if item.available
            ]
        )
        return result

    def run_commands(commands: list[list[str]]):
        """Run commands after container started"""
        for c in commands:
            try:
                logging.info(f"Running command: {c}")
                out, err = client.command.run(
                    RunCommandRequestBodySchema(command=c)
                )
                if out:
                    logging.info(out)
                if err:
                    logging.error(err)
            except Exception as e:
                logging.exception(e)

    # endregion

    any_for_update: bool = bool(
        len([item for item in group.containers if will_update(item)])
        > 0
    )
    if not update or group.is_self or not any_for_update:
        logging.info(
            f"""Group check completed.
================================================================="""
        )
        CACHE.update({"status": ECheckStatus.DONE})
        result.available = _get_shrinked_containers(
            [
                item.container
                for item in group.containers
                if item.available
            ]
        )
        return result

    logging.info("Starting to update a group...")
    CACHE.update({"status": ECheckStatus.UPDATING})

    # Starting from most dependent
    for gc in group.containers[::-1]:
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
                CACHE.update({"status": ECheckStatus.ERROR})
                return on_stop_fail()
        # Stopping all containers
        try:
            logging.info(f"Stopping container {gc.container.name}...")
            client.container.stop(gc.name)
        except Exception as e:
            logging.exception(e)
            logging.error(
                """Failed to stop container. Exiting group update.
================================================================="""
            )
            CACHE.update({"status": ECheckStatus.ERROR})
            return on_stop_fail()

    # Starting from most dependable.
    # At that moment all containers should be stopped.
    # Will update/start them in dependency order

    # Indicates was there an exception during the update
    # If True, the following updates will not be processed.
    any_failed: bool = False
    for gc in group.containers:
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
                client.container.remove(c_name)
                logging.info("Merging configs...")
                merged_config = merge_container_config_with_image(
                    config, new_image
                )
                logging.info("Recreating container...")
                new_c = client.container.create(merged_config)
                logging.info("Starting container...")
                client.container.start(c_name)
                run_commands(gc.commands)
                logging.info("Waiting for healthchecks...")
                if wait_for_container_healthy_sync(client, new_c):
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
                client.container.stop(c_name)
                client.container.remove(c_name)
            except Exception as e:
                logging.exception(e)
                logging.error("Update failed, rolling back...")
                # Try to remove possibly existing container
                if client.container.exists(c_name):
                    logging.warning("Removing failed container...")
                    client.container.stop(c_name)
                    client.container.remove(c_name)
            # Rolling back
            try:
                logging.warning("Tagging previous image...")
                client.image.tag(
                    TagImageRequestBodySchema(
                        spec_or_id=str(old_image.id),
                        tag=image_spec,
                    )
                )
                logging.warning(
                    "Creating container with previous image..."
                )
                rolled_back = client.container.create(config)
                logging.warning("Starting container...")
                client.container.start(str(rolled_back.id))
                run_commands(gc.commands)
                gc.container = rolled_back
                result.rolled_back.append(
                    ShrinkedContainer.from_c(rolled_back)
                )
                logging.warning("Waiting for healthchecks...")
                if wait_for_container_healthy_sync(
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
                client.container.start(gc.name)
                run_commands(gc.commands)
                logging.info("Waiting for healthchecks...")
                if wait_for_container_healthy_sync(
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
    logging.info(
        f"""Group update completed.
================================================================="""
    )
    CACHE.update({"status": ECheckStatus.DONE})
    return result


def check_host(
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
            client.container.list(
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
            res = check_group(client, host, group, update)
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
            output = client.image.prune(
                PruneImagesRequestBodySchema(all=True)
            )
            lines = [
                line.strip()
                for line in output.splitlines()
                if line.strip()
            ]
            result.prune_res = lines[-1] if lines else None

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

        with ThreadPoolExecutor(7) as executor:
            loop = asyncio.get_event_loop()
            tasks: list[asyncio.Future[HostCheckResult | None]] = []
            for h in hosts:
                cli = HostsManager.get_host_client(h)
                t = loop.run_in_executor(
                    executor,
                    lambda: check_host(
                        h,
                        cli,
                        update,
                        host_containers_db.get(h.id, []),
                    ),
                )
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

        async with async_session_maker() as session:
            for r in results:
                await update_containers_data_after_check(r)

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
        return f"    - {c.name}  {c.image_spec}\n"

    title: str = f"Tugtainer ({Config.HOSTNAME})"
    body: str = ""
    for res in results:
        if not res:
            continue
        host_part: str = ""
        if res.updated:
            host_part += "  Updated:\n"
            for c in res.updated:
                host_part += get_cont_str(c)
        if res.available:
            host_part += "  Update available for:\n"
            for c in res.available:
                host_part += get_cont_str(c)
        if res.rolled_back:
            host_part += "  Rolled-back after fail:\n"
            for c in res.rolled_back:
                host_part += get_cont_str(c)
        if res.failed:
            host_part += f"Failed and not rolled-back:\n"
            for c in res.failed:
                host_part += get_cont_str(c)
        if res.prune_res:
            host_part += f"  {res.prune_res}\n"
        if host_part:
            body += f"\nHost: {res.host_name}\n" + host_part
    try:
        if body:
            await send_notification(title, body)
    except Exception as e:
        logging.exception(e)
        logging.error("Failed to send notification")
