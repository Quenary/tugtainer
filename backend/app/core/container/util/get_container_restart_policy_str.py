from python_on_whales.components.container.models import (
    ContainerRestartPolicy,
)


def get_container_restart_policy_str(
    policy: ContainerRestartPolicy | None,
) -> str | None:
    if not policy or not policy.name:
        return None
    policy_str = policy.name
    if policy.maximum_retry_count:
        policy_str += f":{policy.maximum_retry_count}"
    return policy_str
