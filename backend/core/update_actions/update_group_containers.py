from python_on_whales.components.image.models import (
    ImageInspectResult,
)
import logging
from typing import cast
from backend.modules.hosts.hosts_model import HostsModel
from backend.core.action_result import (
    ContainerActionResult,
    GroupActionResult,
)
from backend.enums.action_status_enum import EActionStatus
from backend.core.container_util import (
    wait_for_container_healthy,
    get_container_config,
    merge_container_config_with_image,
    is_running_container,
)
from backend.core.progress.progress_schemas import (
    GroupActionProgress,
)
from backend.core.progress.progress_util import (
    get_group_cache_key,
    is_allowed_start_cache,
)
from backend.core.progress.progress_cache import ProgressCache
from backend.core.container_group.container_group_schemas import (
    ContainerGroupItem,
    ContainerGroup,
)
from backend.core.agent_client import AgentClient
from backend.modules.settings.settings_enum import ESettingKey
from backend.modules.settings.settings_storage import SettingsStorage
from shared.schemas.command_schemas import RunCommandRequestBodySchema
from shared.schemas.container_schemas import (
    CreateContainerRequestBodySchema,
)
from shared.schemas.image_schemas import (
    InspectImageRequestBodySchema,
    PullImageRequestBodySchema,
    TagImageRequestBodySchema,
)
from backend.const import TUGTAINER_PROTECTED_LABEL
from .update_actions_util import update_containers_data_after_action


async def update_group_containers(
    client: AgentClient,
    host: HostsModel,
    group: ContainerGroup,
) -> GroupActionResult | None:
    """
    Update group of containers.
    :param client: docker client
    :param host: docker host
    :param group: group to be updated
    """
    logging.info(
        f"""Starting update of group: '{group.name}', containers count: {len(group.containers)}"""
    )
    STATUS_KEY = get_group_cache_key(host, group)
    CACHE = ProgressCache[GroupActionProgress](STATUS_KEY)
    STATE = CACHE.get()
    if not is_allowed_start_cache(STATE):
        logging.warning(
            f"Update process of {STATUS_KEY} is already running."
        )
        return None

    CACHE.set({"status": EActionStatus.PREPARING})
    for gc in group.containers:
        local_image: ImageInspectResult | None = None
        if gc.container.image:
            local_image = await client.image.inspect(
                InspectImageRequestBodySchema(
                    spec_or_id=gc.container.image
                )
            )
        elif gc.image_spec:
            local_image = await client.image.inspect(
                InspectImageRequestBodySchema(
                    spec_or_id=gc.image_spec
                )
            )
        gc.local_image = local_image

    # region Helper functions
    def _will_update(gc: ContainerGroupItem) -> bool:
        """Whether to update container"""
        updatable = gc.update_available and (
            gc.update_enabled or
            gc.update_manual
        )
        return bool(
            updatable
            and not gc.protected
            and (
                is_running_container(gc.container)
                or not SettingsStorage.get(
                    ESettingKey.UPDATE_ONLY_RUNNING
                )
            )
        )

    def _will_skip(gc: ContainerGroupItem) -> bool:
        """Whether to skip container"""
        if gc.protected:
            logging.info(
                f"Container {gc.name} labeled with {TUGTAINER_PROTECTED_LABEL}, skipping."
            )
            return True
        elif not is_running_container(
            gc.container
        ) and SettingsStorage.get(ESettingKey.UPDATE_ONLY_RUNNING):
            logging.info(
                f"Container {gc.name} is not running, skipping."
            )
            return True
        return False

    def _group_state_to_result(
        group: ContainerGroup,
    ) -> GroupActionResult:
        return GroupActionResult(
            host_id=host.id,
            host_name=host.name,
            items=[
                ContainerActionResult(
                    container=item.container,
                    local_image=item.local_image,
                    remote_image=item.remote_image,
                    local_digests=item.local_digests,
                    remote_digests=item.remote_digests,
                    result=item.result,
                )
                for item in group.containers
            ],
        )

    async def _on_stop_fail():
        """If failed to stop containers before updating"""
        for gc in group.containers:
            await client.container.start(gc.name)
        result = _group_state_to_result(group)
        await update_containers_data_after_action(result)
        CACHE.update(
            {"status": EActionStatus.ERROR, "result": result}
        )
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
    if not any_for_update:
        result = _group_state_to_result(group)
        await update_containers_data_after_action(result)
        logging.info(f"""Group update completed.""")
        CACHE.update({"status": EActionStatus.DONE, "result": result})
        return result

    logging.info("Starting to update a group...")
    CACHE.update({"status": EActionStatus.UPDATING})

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
                    f"""Failed to pull the image for container {gc.container.name} with spec {gc.image_spec}"""
                )
                result = _group_state_to_result(group)
                await update_containers_data_after_action(result)
                CACHE.update(
                    {"status": EActionStatus.ERROR, "result": result}
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
                    """Failed to get config for updatable container. Exiting group update."""
                )
                return await _on_stop_fail()
        try:
            logging.info(f"Stopping container {gc.container.name}...")
            await client.container.stop(gc.name)
        except Exception as e:
            logging.exception(e)
            logging.error(
                """Failed to stop container. Exiting group update."""
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
        was_running = is_running_container(gc.container)
        # Updating container
        if _will_update(gc) and not any_failed:
            image_spec = cast(str, gc.image_spec)
            local_image = cast(ImageInspectResult, gc.local_image)
            remote_image = cast(ImageInspectResult, gc.remote_image)
            config = cast(CreateContainerRequestBodySchema, gc.config)
            logging.info(f"Starting update of container {gc.name}...")
            try:
                logging.info("Removing container...")
                await client.container.remove(gc.name)
                logging.info("Merging configs...")
                merged_config = merge_container_config_with_image(
                    config, remote_image
                )
                logging.info("Recreating container...")
                new_c = await client.container.create(merged_config)
                if not was_running:
                    logging.info(
                        "Container recreated. It wasn't running before update, consider as success and continue..."
                    )
                    continue
                logging.info("Starting container...")
                await client.container.start(gc.name)
                await _run_commands(gc.commands)
                logging.info("Waiting for healthchecks...")
                if await wait_for_container_healthy(
                    client, new_c, host.container_hc_timeout
                ):
                    logging.info("Container is healthy!")
                    gc.container = new_c
                    gc.result = "updated"
                    continue
                # Failed healthchecks
                logging.warning(
                    "Container is unhealthy, rolling back..."
                )
                await client.container.stop(gc.name)
                await client.container.remove(gc.name)
            except Exception as e:
                logging.exception(e)
                logging.error("Update failed, rolling back...")
                # Try to remove possibly existing container
                try:
                    if await client.container.exists(gc.name):
                        logging.warning(
                            "Removing failed container..."
                        )
                        await client.container.stop(gc.name)
                        await client.container.remove(gc.name)
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
                gc.result = "rolled_back"
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
                gc.result = "failed"
                any_failed = True
        # Start not updatable container
        else:
            try:
                if not was_running:
                    logging.info(
                        f"Container {gc.name} wasn't running before update, continue..."
                    )
                    continue
                logging.info(
                    f"Starting non-updatable container {gc.name}"
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
    await update_containers_data_after_action(result)
    logging.info(f"""Group update completed.""")
    CACHE.update({"status": EActionStatus.DONE, "result": result})
    return result
