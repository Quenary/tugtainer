from shared.runtime.runtime_models import (
    ContainerInspectResult,
)


def is_running_container(container: ContainerInspectResult) -> bool:
    return bool(container.state and container.state.status == "running")
