import asyncio
import logging
from typing import Final, cast

from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from python_on_whales.components.image.models import (
    ImageInspectResult,
)

from backend.core.action_result import (
    ContainerActionResult,
    UpdatePlanResult,
)
from backend.core.agent_client import AgentClient
from backend.core.container_util.container_config import (
    get_container_config,
    merge_container_config_with_image,
)
from backend.core.container_util.get_container_image_spec import (
    get_container_image_spec,
)
from backend.core.container_util.is_running_container import is_running_container
from backend.core.container_util.wait_for_container_healthy import (
    wait_for_container_healthy,
)
from backend.core.progress.progress_cache import ProgressCache
from backend.core.progress.progress_schemas import UpdatePlanProgress
from backend.core.progress.progress_util import (
    get_plan_cache_key,
    is_allowed_start_cache,
)
from backend.core.update_actions.update_actions_schema import (
    UpdatePlan,
    UpdatePlanItem,
)
from backend.core.update_actions.update_actions_util import (
    disconnect_all_networks,
    update_containers_data_after_execution,
)
from backend.enums.action_status_enum import EActionStatus
from backend.modules.hosts.hosts_model import HostsModel
from backend.modules.settings.settings_enum import ESettingKey
from backend.modules.settings.settings_storage import SettingsStorage
from backend.util.jitter import jitter
from shared.schemas.command_schemas import RunCommandRequestBodySchema
from shared.schemas.container_schemas import (
    CreateContainerRequestBodySchema,
)
from shared.schemas.docker_version_scheme import DockerVersionScheme
from shared.schemas.image_schemas import (
    InspectImageRequestBodySchema,
    PullImageRequestBodySchema,
    TagImageRequestBodySchema,
)

logger: Final = logging.getLogger("execute_update_plan")


async def execute_update_plan(
    client: AgentClient,
    host: HostsModel,
    containers: list[ContainerInspectResult],
    plan: UpdatePlan,
    docker_version: DockerVersionScheme | None,
) -> UpdatePlanResult | None:
    logger.info(
        f"to_update={plan.to_update}, affected={plan.affected}, order={plan.order}"
    )
    delay: Final = SettingsStorage.get(ESettingKey.REGISTRY_REQ_DELAY)
    status_key: Final = get_plan_cache_key(host, plan)
    cache: Final = ProgressCache[UpdatePlanProgress](status_key)
    state: Final = cache.get()
    if not is_allowed_start_cache(state):
        logger.warning(f"{status_key} is already running. Exiting.")
        return None

    if not plan.to_update:
        logger.warning(f"{status_key} has no containers to update. Exiting.")
        return None

    cache.set({"status": EActionStatus.PREPARING})

    items: Final = [
        UpdatePlanItem(
            container=c,
            image_spec=get_container_image_spec(c),
            was_running=is_running_container(c),
        )
        for c in containers
        if c.name in plan.to_update or c.name in plan.affected
    ]
    items_map: Final = {item.name: item for item in items}

    # Prepare updatable containers state
    # This part of code should not raise
    # We will check the state before updating
    for item in items:
        if item.name in plan.to_update:
            # Get local image
            try:
                logger.info(f"Getting local image for {item.name}")
                if item.container.image:
                    local_image = await client.image.inspect(
                        InspectImageRequestBodySchema(spec_or_id=item.container.image)
                    )
                elif item.image_spec:
                    local_image = await client.image.inspect(
                        InspectImageRequestBodySchema(spec_or_id=item.image_spec)
                    )
                else:
                    raise Exception("No image id or image spec specified")
                item.local_image = local_image
            except Exception as e:
                logger.exception(f"Failed to get local image for {item.name}")
                item.errors.append(e)

            # Pull new image
            try:
                logger.info(f"Pulling image for {item.name}")
                remote_image = await client.image.pull(
                    PullImageRequestBodySchema(image=cast(str, item.image_spec))
                )
                item.remote_image = remote_image
            except Exception as e:
                logger.exception(f"Failed to pull image for {item.name}")
                item.errors.append(e)

            # Prepare config
            try:
                logger.info(f"Getting config for {item.name}")
                config, commands = get_container_config(
                    item.container,
                    docker_version,
                )
                item.config = config
                item.commands = commands
            except Exception as e:
                logger.exception(f"Failed to get config for {item.name}")
                item.errors.append(e)

            await asyncio.sleep(jitter(delay))

    def _can_update(item: UpdatePlanItem) -> bool:
        return bool(
            item
            and item.local_image
            and item.remote_image
            and item.config
            and not item.errors
        )

    cache.update({"status": EActionStatus.UPDATING})

    # Stopping containers in order
    # from most dependent to most dependable
    for name in reversed(plan.order):
        item = items_map.get(name)
        if item and item.was_running:
            try:
                logger.info(f"Stopping container {name}")
                await client.container.stop(name)
                item.container = await client.container.inspect(name)
            except Exception as e:
                logger.exception(f"Failed to stop container {name}")
                item.errors.append(e)

    async def _attempt_start_with_health(item: UpdatePlanItem):
        """
        Try to start a container with waiting for healthchecks.
        Mutates the item's container attribute.
        """
        if not item.was_running:
            logger.info(f"{item.name} wasn't running before execution, continue...")
            return

        item.container = await client.container.inspect(item.name)
        if is_running_container(item.container):
            logger.info(f"{item.name} already running, continue...")
            return

        logger.info(f"Starting container {item.name}")
        await client.container.start(item.name)

        logger.info("Waiting for healthchecks...")
        healthy, container = await wait_for_container_healthy(
            client,
            item.container,
            host.container_hc_timeout,
        )
        item.container = container
        if healthy:
            logger.info("Container is healthy!")
            return
        raise Exception(f"{item.name} is unhealthy!")

    async def _run_commands(item: UpdatePlanItem):
        """Run commands after container started"""
        for c in item.commands:
            try:
                logger.info(f"Running command: {c}")
                out, err = await client.command.run(
                    RunCommandRequestBodySchema(command=c)
                )
                if out:
                    logger.info(out)
                if err:
                    logger.error(err)
            except Exception as e:
                logger.exception(f"Error while running command {c}")
                item.errors.append(e)

    # Updating and/or starting containers in order
    # from most dependable to most dependent
    for name in plan.order:
        item = items_map.get(name)
        if item:
            # Updating containers
            if name in plan.to_update:
                if not _can_update(item):
                    logger.warning(f"Cannot update {item.name} due to prior errors")
                    try:
                        await _attempt_start_with_health(item)
                    except Exception as e:
                        logger.exception(
                            f"Error while starting {item.name}. Continue..."
                        )
                        item.errors.append(e)
                    continue

                logger.info(f"Starting update of {item.name}")
                image_spec = cast(str, item.image_spec)
                local_image = cast(ImageInspectResult, item.local_image)
                remote_image = cast(ImageInspectResult, item.remote_image)
                config = cast(CreateContainerRequestBodySchema, item.config)

                try:
                    await disconnect_all_networks(client, item.container, True)

                    logger.info("Removing container...")
                    await client.container.remove(item.name)

                    logger.info("Merging configs")
                    merged_config = merge_container_config_with_image(
                        config, remote_image
                    )

                    logger.info("Recreating container...")
                    item.container = await client.container.create(merged_config)
                    if not item.was_running:
                        logger.info(
                            "Container recreated. It wasn't running before update, consider as success and continue..."
                        )
                        item.result = "updated"
                        continue

                    logger.info("Starting container...")
                    await client.container.start(item.name)
                    await _run_commands(item)
                    item.container = await client.container.inspect(item.name)

                    logger.info("Waiting for healthchecks...")
                    healthy, container = await wait_for_container_healthy(
                        client,
                        item.container,
                        host.container_hc_timeout,
                    )
                    item.container = container
                    if healthy:
                        logger.info("Container is healthy!")
                        item.result = "updated"
                        continue

                    logger.warning("Container is unhealthy, rolling back...")
                    await client.container.stop(item.name)
                    await disconnect_all_networks(client, item.container, True)
                    await client.container.remove(item.name)
                except Exception as e:
                    logger.exception(
                        f"Failed to update {item.name}, cleanup before rollback..."
                    )
                    item.errors.append(e)
                    # Cleanup after update error
                    try:
                        if await client.container.exists(item.name):
                            logger.warning("Removing failed container")
                            await client.container.stop(item.name)
                            await disconnect_all_networks(client, item.container, True)
                            await client.container.remove(name_or_id=item.name)
                    except Exception as e:
                        logger.exception("Cleanup error")
                        item.errors.append(e)

                # Rolling back
                try:
                    logger.warning(
                        f"Tagging previous image of {item.name} with {item.image_spec}"
                    )
                    await client.image.tag(
                        TagImageRequestBodySchema(
                            spec_or_id=str(local_image.id),
                            tag=image_spec,
                        )
                    )
                except Exception as e:
                    logger.exception("Failed to tag previous image")
                    item.errors.append(e)
                try:
                    logger.warning("Creating container with previous configuration...")
                    item.container = await client.container.create(config)

                    logger.warning("Starting container...")
                    await client.container.start(item.name)
                    await _run_commands(item)
                    item.container = await client.container.inspect(item.name)
                    item.result = "rolled_back"

                    logger.warning("Waiting for healthchecks...")
                    healthy, container = await wait_for_container_healthy(
                        client,
                        item.container,
                        host.container_hc_timeout,
                    )
                    item.container = container
                    if healthy:
                        logger.warning("Container is heailthy after rolling back!")
                        continue
                    logger.error("Container is unhealthy after rolling back!")
                except Exception as e:
                    logger.exception("Error while rolling back!")
                    item.errors.append(e)
                    item.result = "failed"

            # Starting non-updatable containers
            if name in plan.affected:
                try:
                    await _attempt_start_with_health(item)
                except Exception as e:
                    logger.exception(f"Error while starting {item.name}. Continue...")
                    item.errors.append(e)

    logger.info("Finished plan execution")

    errors_count = sum(len(item.errors) for item in items)
    if errors_count:
        logger.warning(f"Total errors: {errors_count} (see logs for details)")

    result: Final = UpdatePlanResult(
        host_id=host.id,
        host_name=host.name,
        items=[
            ContainerActionResult(
                container=item.container,
                local_image=item.local_image,
                remote_image=item.remote_image,
                result=item.result,
            )
            for item in items
        ],
    )

    await update_containers_data_after_execution(result)

    cache.update(
        {
            "status": EActionStatus.DONE,
            "result": result,
        }
    )

    return result
