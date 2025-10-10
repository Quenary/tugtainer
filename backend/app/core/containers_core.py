from python_on_whales import docker, Container, Image
from python_on_whales.utils import run as docker_run_cmd
import logging
from typing import NotRequired, TypedDict
from sqlalchemy import and_, select
import asyncio
import concurrent.futures
from app.db import (
    ContainersModel,
    async_session_maker,
    get_setting_from_db,
    get_setting_typed_value,
)
from app.core.notifications_core import send_notification
from app.enums.check_status_enum import ECheckStatus
from app.helpers import (
    is_self_container,
    now,
)
import traceback
from app.config import Config
from app.enums.settings_enum import ESettingKey
from app.core.container.util import (
    get_container_image_spec,
    get_container_image_id,
    wait_for_container_healthy,
    update_container_db_data,
    get_container_config,
    merge_container_config_with_image,
)
from app.core.container import (
    ContainerCheckData,
    AllContainersCheckData,
    ProcessCache,
)

_ALL_CONTAINERS_STATUS_KEY = "check_and_update_all_containers"


async def filter_containers_for_check(
    containers: list[Container],
) -> list[Container]:
    """
    Filter containers marked for check only
    as well as self container
    """
    async with async_session_maker() as session:
        stmt = select(ContainersModel.name).where(
            and_(
                ContainersModel.check_enabled == True,
                ContainersModel.update_enabled == False,
            )
        )
        result = await session.execute(stmt)
        names = result.scalars().all()
        res: list[Container] = []
        for c in containers:
            if c.name in names or is_self_container(c):
                res.append(c)
        return res


async def filter_containers_for_update(
    containers: list[Container],
) -> list[Container]:
    """Filter containers marked for check and auto update"""
    async with async_session_maker() as session:
        stmt = select(ContainersModel.name).where(
            and_(
                ContainersModel.check_enabled == True,
                ContainersModel.update_enabled == True,
            )
        )
        result = await session.execute(stmt)
        names = result.scalars().all()
        return [c for c in containers if c.name in names]


def get_service_name(container: Container) -> str:
    """Extract service name from labels"""
    labels = container.config.labels or {}
    return labels.get("com.docker.compose.service", container.name)


def get_dependencies(container: Container) -> list[str]:
    """Get list of dependencies (container names)"""
    labels: dict[str, str] = container.config.labels or {}

    # E.g. "service1:condition:value,service2:condition:value"
    depends_on_label: str = labels.get(
        "com.docker.compose.depends_on", ""
    )

    if not depends_on_label:
        return []

    dependencies: list[str] = []
    for dep in depends_on_label.split(","):
        parts = dep.split(":")
        if parts:  # Берем только имя сервиса (первую часть)
            dependencies.append(parts[0])

    return dependencies


def _sort_containers_by_dependencies(
    containers: list[Container],
) -> list[Container]:
    """
    Sort containers so that those on which others depend come first.
    Use the com.docker.compose.depends_on label, if present.
    """
    # Создаем словарь зависимостей: сервис -> список зависимостей
    container_map: dict[str, Container] = {}
    dependencies: dict[str, list[str]] = {}

    for container in containers:
        service_name = get_service_name(container)
        container_map[service_name] = container
        dependencies[service_name] = get_dependencies(container)

    visited: set[str] = set()
    result: list[Container] = []

    def visit(service) -> None:
        if service in visited:
            return
        visited.add(service)

        # Check all dependencies first
        for dep in dependencies[service]:
            if dep in container_map:
                visit(dep)

        # Then add current service
        if service in container_map:
            result.append(container_map[service])

    for service in container_map:
        visit(service)

    return result


async def _recreate_container(
    existing_container: Container,
    old_image: Image,
    new_image: Image,
) -> tuple[Container | None, bool]:
    """
    Recreate container with new image.
    :param container: container object
    :param new_image: new image name
    :returns 0: Container object (new or rolled-back)
    :returns 1: Updated flag (that is, not rolled-back)
    Could raise an exception if recreate and rallback fails.
    """

    NAME: str = existing_container.name
    IMAGE_SPEC = str(get_container_image_spec(existing_container))
    CURRENT_CFG, COMMANDS = get_container_config(existing_container)
    SHOULD_START = existing_container.state.status == "running"
    LOOP = asyncio.get_running_loop()

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=1
    ) as executor:

        async def run_commands_after_create():
            for C in COMMANDS:
                try:
                    _command = docker.config.docker_cmd + C
                    logging.info(f"Running command: {_command}")
                    out, err = await LOOP.run_in_executor(
                        executor, lambda: docker_run_cmd(_command)
                    )
                    if out:
                        logging.info(out)
                    if err:
                        logging.error(err)
                except Exception as e:
                    logging.error(f"Error while running command: {C}")
                    logging.exception(e)

        try:
            logging.info(f"Merging container and new image values")
            MERGED_CFG = merge_container_config_with_image(
                CURRENT_CFG, new_image
            )

            logging.info(f"Stopping container {NAME}...")
            await LOOP.run_in_executor(
                executor, existing_container.stop
            )

            logging.info(f"Removing container {NAME}...")
            await LOOP.run_in_executor(
                executor, existing_container.remove
            )

            logging.info(f"Creating new container {NAME}...")
            new_container = await LOOP.run_in_executor(
                executor,
                lambda: docker.container.create(
                    IMAGE_SPEC,
                    **MERGED_CFG,
                ),
            )

            await run_commands_after_create()

            if not SHOULD_START:
                logging.info(
                    f"Container {NAME} was not running before update, so leave it as is..."
                )
                return (new_container, True)

            logging.info(f"Starting new container {NAME}...")
            await LOOP.run_in_executor(
                executor, lambda: new_container.start()
            )

            logging.info(f"Waiting for healthchecks of {NAME}")
            if await wait_for_container_healthy(new_container):
                logging.info(
                    f"Container {NAME} is healthy. Update successful."
                )
                return (new_container, True)

            logging.warning(
                f"Container {NAME} failed healthcheck. Rolling back..."
            )
            await LOOP.run_in_executor(executor, new_container.stop)
            await LOOP.run_in_executor(executor, new_container.remove)
            raise RuntimeError("Healthcheck failed")
        except Exception as e:
            logging.exception(e)
            logging.warning(
                f"Rolling back {NAME} with previous image"
            )
            try:
                # In case failed container was not removed
                failed_cont = docker.container.inspect(NAME)
                if failed_cont:
                    await LOOP.run_in_executor(
                        executor, failed_cont.stop
                    )
                    await LOOP.run_in_executor(
                        executor, failed_cont.remove
                    )
            except:
                pass
            logging.warning(
                f"Tagging previous image with spec: {IMAGE_SPEC}"
            )
            await LOOP.run_in_executor(
                executor, lambda: old_image.tag(IMAGE_SPEC)
            )
            logging.warning(f"Creating container with previous image")
            rolled_back = await LOOP.run_in_executor(
                executor,
                lambda: docker.container.create(
                    image=IMAGE_SPEC,
                    **CURRENT_CFG,
                ),
            )
            await run_commands_after_create()
            if SHOULD_START:
                logging.info(f"Starting rolled-back container")
                await LOOP.run_in_executor(
                    executor, rolled_back.start
                )
            logging.info(f"Rollback complete for {NAME}.")
            return (rolled_back, False)


class CheckContainerResult(TypedDict):
    container: NotRequired[Container | None]
    available: bool  # new image found, but not updated
    updated: bool  # updated flag
    exception: NotRequired[Exception]


async def check_container(
    name: str, update: bool = False
) -> CheckContainerResult:
    """
    Check and update one container.
    Should not raises errors, only logging.
    :param name: name or id
    :param update: whether to update container (only check if false)
    """
    CACHE = ProcessCache[ContainerCheckData](name)
    try:
        STATUS = CACHE.get()
        ALLOW_STATUSES = [ECheckStatus.DONE, ECheckStatus.ERROR]
        LOOP = asyncio.get_running_loop()

        if STATUS and STATUS.get("status") not in ALLOW_STATUSES:
            logging.warning(
                f"Check and update of container {name} is already running"
            )
            return CheckContainerResult(
                available=False, updated=False
            )

        CACHE.set({"status": ECheckStatus.PREPARING})
        container = await LOOP.run_in_executor(
            None, lambda: docker.container.inspect(name)
        )
        if not container:
            CACHE.update({"status": ECheckStatus.DONE})
            logging.warning(
                f"Container '{name}' not found, cannot check for update"
            )
            return CheckContainerResult(
                available=False, updated=False
            )

        CACHE.update({"status": ECheckStatus.CHECKING})
        logging.info(
            f"Start checking for updates of container '{name}'"
        )
        IMAGE_SPEC = get_container_image_spec(container)
        if not IMAGE_SPEC:
            CACHE.update({"status": ECheckStatus.DONE})
            logging.warning(
                f"Cannot check container '{name}' without image spec."
            )
            return CheckContainerResult(
                available=False, updated=False
            )

        IMAGE_ID = get_container_image_id(container)
        OLD_IMAGE: Image
        if IMAGE_ID:
            OLD_IMAGE = await LOOP.run_in_executor(
                None, lambda: docker.image.inspect(IMAGE_ID)
            )
        else:
            OLD_IMAGE = await LOOP.run_in_executor(
                None, lambda: docker.image.inspect(IMAGE_SPEC)
            )
        if not OLD_IMAGE.repo_digests:
            CACHE.update({"status": ECheckStatus.DONE})
            logging.warning(
                f"Image of '{name}' missing repo digests. Presumably a local image. Exiting."
            )
            return CheckContainerResult(
                available=False, updated=False
            )

        NEW_IMAGE = await LOOP.run_in_executor(
            None, lambda: docker.image.pull(IMAGE_SPEC)
        )
        if not isinstance(NEW_IMAGE, Image):
            CACHE.update({"status": ECheckStatus.DONE})
            logging.warning(f"Failed to pull new image for '{name}'")
            return CheckContainerResult(
                available=False, updated=False
            )
        update_available: bool = bool(
            OLD_IMAGE
            and NEW_IMAGE
            and OLD_IMAGE.repo_digests != NEW_IMAGE.repo_digests
        )
        await update_container_db_data(
            str(name),
            {
                "update_available": update_available,
                "checked_at": now(),
            },
        )

        if not update_available:
            CACHE.update({"status": ECheckStatus.DONE})
            logging.info(
                f"No new image was found for the container '{name}'"
            )
            return CheckContainerResult(
                available=False, updated=False
            )

        logging.info(f"New image found for the container '{name}'")

        is_self = is_self_container(container)
        if is_self:
            CACHE.update({"status": ECheckStatus.DONE})
            logging.info(
                f"Update is available, but self container cannot be updated with that func"
            )
            return CheckContainerResult(available=True, updated=False)

        if not update:
            CACHE.update({"status": ECheckStatus.DONE})
            logging.info(f"Check of container '{name}' complete")
            return CheckContainerResult(available=True, updated=False)

        CACHE.update({"status": ECheckStatus.UPDATING})
        try:
            container, updated = await _recreate_container(
                container, OLD_IMAGE, NEW_IMAGE
            )
            if updated:
                await update_container_db_data(
                    str(name),
                    {
                        "update_available": False,
                        "updated_at": now(),
                    },
                )
            CACHE.update({"status": ECheckStatus.DONE})
            return CheckContainerResult(
                container=container, available=False, updated=updated
            )
        except Exception as e:
            logging.error(f"Failed to update container '{name}'")
            logging.exception(e)
            CACHE.update({"status": ECheckStatus.ERROR})
            return CheckContainerResult(
                available=True, updated=False, exception=e
            )
    except Exception as e:
        logging.error(
            f"Error while checking container '{name}' update:"
        )
        logging.exception(e)
        CACHE.update({"status": ECheckStatus.ERROR})
        return CheckContainerResult(
            available=False, updated=False, exception=e
        )


async def check_and_update_all_containers():
    """
    Check and update containers
    marked for it, as well as self container (check only).
    Should not raises errors, only logging.
    """
    CACHE = ProcessCache[AllContainersCheckData](
        _ALL_CONTAINERS_STATUS_KEY
    )
    status = CACHE.get()
    allow_statuses = [ECheckStatus.DONE, ECheckStatus.ERROR]
    if status and status.get("status") not in allow_statuses:
        logging.warning(
            "Check and update process is already running."
        )
        return

    CACHE.set(
        {"status": ECheckStatus.PREPARING},
    )
    logging.info("Start checking for updates of all containers")
    containers: list[Container] = docker.container.list(all=True)

    for_check = await filter_containers_for_check(containers)
    for_update = await filter_containers_for_update(containers)
    for_update = _sort_containers_by_dependencies(for_update)

    CACHE.update(
        {"status": ECheckStatus.CHECKING},
    )

    available: list[Container] = []
    updated: list[Container] = []
    rolledback: list[Container] = []
    failed: list[Container] = []
    errors: list[Exception] = []

    for item in for_check:
        res = await check_container(item.name, False)
        _available = res["available"]
        _exp = res.get("exception")
        if _available:
            available.append(item)
        elif _exp:
            errors.append(_exp)
            failed.append(item)

    CACHE.update(
        {
            "status": ECheckStatus.UPDATING,
            "available": len(available),
        },
    )

    for item in for_update:
        res = await check_container(str(item.name), True)
        _cont = res.get("container")
        _updated = res.get("updated")
        _exp = res.get("exception")
        if _cont:
            if _updated:
                updated.append(_cont)
            else:
                rolledback.append(_cont)
        elif _exp:
            errors.append(_exp)
            failed.append(item)

    CACHE.update(
        {
            "status": ECheckStatus.DONE,
            "updated": len(updated),
            "failed": len(failed),
            "rolledback": len(rolledback),
        },
    )

    prune_images = await get_setting_from_db(ESettingKey.PRUNE_IMAGES)
    prune_res: str | None = None
    if get_setting_typed_value(
        prune_images.value, prune_images.value_type
    ):
        loop = asyncio.get_running_loop()
        output = await loop.run_in_executor(
            None, lambda: docker.image.prune()
        )
        lines = [
            line.strip()
            for line in output.splitlines()
            if line.strip()
        ]
        prune_res = lines[-1] if lines else None

    # Notification
    try:
        title: str = f"Tugtainer ({Config.HOSTNAME})"
        body: str = ""
        if updated:
            body += "Updated:\n"
            for c in updated:
                body += f"{c.name} {get_container_image_spec(c)}\n"
            body += "\n"
        if available:
            body += "Update available for:\n"
            for c in available:
                body += f"{c.name} {get_container_image_spec(c)}\n"
            body += "\n"
        if rolledback:
            body += "Rolled-back after fail:\n"
            for c in rolledback:
                body += f"{c.name} {get_container_image_spec(c)}\n"
        if failed:
            body += f"Failed and not rolled-back:\n"
            for c in failed:
                body += f"{c.name} {get_container_image_spec(c)}\n\n"
        if errors:
            body += f"Several errors occured:\n"
            for e in errors:
                tb_lines = traceback.format_exception(
                    type(e), e, e.__traceback__
                )
                last_lines = tb_lines[-3:]
                body += "".join(last_lines) + "\n"
        if prune_res:
            body += prune_res
        if body:
            await send_notification(title, body)
    except Exception as e:
        logging.error(f"Error while sending notification: {e}")
