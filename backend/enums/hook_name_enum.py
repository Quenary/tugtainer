from enum import StrEnum


class EHookName(StrEnum):
    """
    Enum of container update lifecycle hook names.
    Values must match the field names on
    backend.modules.containers.containers_schemas.ContainerHooks exactly,
    since hooks_executor.run_hooks() looks up commands via getattr(hooks, name.value).
    """

    PRE_UPDATE = "pre_update"
    POST_UPDATE = "post_update"
    PRE_STOP = "pre_stop"
    PRE_ROLLBACK = "pre_rollback"
    POST_ROLLBACK = "post_rollback"
