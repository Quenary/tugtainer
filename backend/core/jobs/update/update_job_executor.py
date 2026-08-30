import asyncio
import logging
from typing import Final, cast

from python_on_whales.components.container.models import (
    ContainerInspectResult,
)
from python_on_whales.components.image.models import (
    ImageInspectResult,
)

from backend.config import Config
from backend.core.agent_client import AgentClient
from backend.core.container_util.container_config import (
    diff_container_config_with_image,
    get_container_config,
)
from backend.core.container_util.get_container_image_spec import (
    get_container_image_spec,
)
from backend.core.container_util.is_running_container import is_running_container
from backend.core.container_util.wait_for_container_healthy import (
    wait_for_container_healthy,
)
from backend.core.jobs.jobs_results import ContainerJobResult
from backend.core.jobs.jobs_tracker import HostJobTracker
from backend.core.jobs.update.update_hooks import get_hooks_map, run_hooks
from backend.core.jobs.update.update_job_plan_builder import UpdateJobPlan
from backend.core.jobs.update.update_job_plan_item import UpdateJobPlanItem
from backend.core.jobs.update.update_previous_image import (
    get_previous_image_for_result,
)
from backend.core.jobs.update.update_util import (
    disconnect_all_networks,
    update_containers_data_after_execution,
)
from backend.enums.hook_name_enum import EHookName
from backend.enums.job_status_enum import EJobStatus
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

logger: Final = logging.getLogger("execute_update_job")


async def execute_update_job(
    client: AgentClient,
    host: HostsModel,
    containers: list[ContainerInspectResult],
    plan: UpdateJobPlan,
    docker_version: DockerVersionScheme | None,
    tracker: HostJobTracker | None = None,
) -> list[ContainerJobResult]:
    logger.info(
        f"to_update={plan.to_update}, affected={plan.affected}, order={plan.order}"
    )
    delay: Final = SettingsStorage.get(ESettingKey.REGISTRY_REQ_DELAY)

    if not plan.to_update:
        logger.warning("Update plan has no containers to update. Exiting.")
        return []

    def _slot(
        name: str,
        status: EJobStatus,
        result: ContainerJobResult | None = None,
    ) -> None:
        if tracker:
            tracker.set_container(name, status, result)

    items: Final = [
        UpdateJobPlanItem(
            container=c,
            image_spec=get_container_image_spec(c),
            was_running=is_running_container(c),
        )
        for c in containers
        if c.name in plan.to_update or c.name in plan.affected
    ]
    items_map: Final = {item.name: item for item in items}

    hooks_map: Final = (
        await get_hooks_map(host.id, list(items_map.keys()))
        if Config.ALLOW_HOOKS
        else {}
    )

    # Prepare updatable containers state
    # This part of code should not raise
    # We will check the state before updating
    for item in items:
        if item.name in plan.to_update:
            _slot(item.name, EJobStatus.PREPARING)
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
                    item.local_image,
                    docker_version,
                )
                item.config = config
                item.commands = commands
            except Exception as e:
                logger.exception(f"Failed to get config for {item.name}")
                item.errors.append(e)

            await asyncio.sleep(jitter(delay))

    def _can_update(item: UpdateJobPlanItem) -> bool:
        return bool(
            item
            and item.local_image
            and item.remote_image
            and item.config
            and not item.errors
        )

    # Stopping containers in order
    # from most dependent to most dependable
    for name in reversed(plan.order):
        item = items_map.get(name)
        if item and item.was_running:
            hooks = hooks_map.get(name)
            hook_errors = await run_hooks(client, name, hooks, EHookName.PRE_STOP)
            if not hook_errors and name in plan.to_update:
                hook_errors = await run_hooks(client, name, hooks, EHookName.PRE_UPDATE)
            if hook_errors:
                item.errors.extend(hook_errors)
                logger.warning(
                    f"Skipping stop of {name} due to pre_stop/pre_update hook failure"
                )
                continue
            try:
                logger.info(f"Stopping container {name}")
                await client.container.stop(name)
                item.container = await client.container.inspect(name)
            except Exception as e:
                logger.exception(f"Failed to stop container {name}")
                item.errors.append(e)

    async def _attempt_start_with_health(item: UpdateJobPlanItem):
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

    async def _run_commands(item: UpdateJobPlanItem):
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
            _slot(name, EJobStatus.UPDATING)
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
                    # Refresh the attachment list when possible, but always
                    # attempt the disconnect: a force disconnect also clears
                    # endpoints left behind by an already gone container.
                    if await client.container.exists(item.name):
                        item.container = await client.container.inspect(item.name)
                    await disconnect_all_networks(client, item.container, True)

                    logger.info("Removing container...")
                    await client.container.remove(item.name)

                    logger.info("Merging configs")
                    merged_config = diff_container_config_with_image(
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
                        hook_errors = await run_hooks(
                            client,
                            item.name,
                            hooks_map.get(item.name),
                            EHookName.POST_UPDATE,
                        )
                        item.errors.extend(hook_errors)
                        continue

                    logger.warning("Container is unhealthy, rolling back...")
                    hook_errors = await run_hooks(
                        client,
                        item.name,
                        hooks_map.get(item.name),
                        EHookName.PRE_ROLLBACK,
                    )
                    item.errors.extend(hook_errors)
                    await client.container.stop(item.name)
                    item.container = await client.container.inspect(item.name)
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
                            existing = await client.container.inspect(item.name)
                            item.container = existing
                            if is_running_container(existing):
                                hook_errors = await run_hooks(
                                    client,
                                    item.name,
                                    hooks_map.get(item.name),
                                    EHookName.PRE_ROLLBACK,
                                )
                                item.errors.extend(hook_errors)
                            logger.warning("Removing failed container")
                            await client.container.stop(item.name)
                            existing = await client.container.inspect(item.name)
                            item.container = existing
                            await disconnect_all_networks(client, existing, True)
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
                    hook_errors = await run_hooks(
                        client,
                        item.name,
                        hooks_map.get(item.name),
                        EHookName.POST_ROLLBACK,
                    )
                    item.errors.extend(hook_errors)

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

    def _to_job_result(item: UpdateJobPlanItem) -> ContainerJobResult:
        previous = get_previous_image_for_result(item.local_image, item.result)
        return ContainerJobResult(
            container=item.container,
            local_image=item.local_image,
            remote_image=item.remote_image,
            result=item.result,
            previous_image_digests=previous.digests,
            previous_image_tags=previous.tags,
            previous_image_version=previous.version,
        )

    results = [_to_job_result(item) for item in items]

    for item, item_result in zip(items, results, strict=True):
        slot_status = (
            EJobStatus.ERROR
            if item.errors and item.result in (None, "failed")
            else EJobStatus.DONE
        )
        _slot(item.name, slot_status, item_result)

    await update_containers_data_after_execution(host.id, results)

    return results
