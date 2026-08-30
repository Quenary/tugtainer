import logging
from typing import Final

from sqlalchemy import select

from backend.core.agent_client import AgentClient
from backend.db.session import async_session_maker
from backend.enums.hook_name_enum import EHookName
from backend.modules.containers.containers_model import ContainersModel
from backend.modules.containers.containers_schemas import ContainerHooks
from shared.schemas.container_schemas import ExecContainerRequestBodySchema

logger: Final = logging.getLogger("update_hooks")


async def get_hooks_map(
    host_id: int, names: list[str]
) -> dict[str, ContainerHooks]:
    """
    Load hooks configuration for the given containers from db in one query.
    Names with no db row are simply absent from the result.
    """
    if not names:
        return {}
    async with async_session_maker() as session:
        rows = await session.scalars(
            select(ContainersModel).where(
                ContainersModel.host_id == host_id,
                ContainersModel.name.in_(names),
            )
        )
        return {
            row.name: ContainerHooks.model_validate(row.hooks or {})
            for row in rows
        }


async def run_hooks(
    client: AgentClient,
    container_name: str,
    hooks: ContainerHooks | None,
    hook_name: EHookName,
) -> list[Exception]:
    """
    Run every command configured for hook_name sequentially inside
    container_name via the agent's exec endpoint.
    Never raises - collects and returns errors instead, so callers decide
    whether a given hook's failures should abort the caller's flow
    (pre_update/pre_stop) or just be logged (post_update/pre_rollback/post_rollback).
    """
    if not hooks:
        return []
    commands = getattr(hooks, hook_name.value)
    errors: list[Exception] = []
    for command in commands:
        try:
            logger.info(
                f"Running {hook_name.value} hook for {container_name}: {command}"
            )
            await client.container.exec(
                container_name,
                ExecContainerRequestBodySchema(command=command),
            )
        except Exception as e:
            logger.exception(
                f"Error while running {hook_name.value} hook for {container_name}"
            )
            errors.append(e)
    return errors
