from python_on_whales.components.container.models import Mount


def map_mounts_to_arg(
    mounts_config: list[Mount],
) -> list[list[str]]:
    """
    Map docker inspect mounts config to run/create arg
    """
    docker_mounts: list[list[str]] = []

    for mount in mounts_config:
        mount_list: list[str] = []

        source = mount.source  # might be changed later

        type = mount.type or "volume"
        mount_list.append(f"type={type}")

        dst = mount.destination
        if dst:
            mount_list.append(f"dst={dst}")

        read_only: bool = mount.rw == False
        if read_only:
            mount_list.append("readonly")

        if type == "bind":
            mode_parts = mount.mode.split(",") if mount.mode else []
            for consistency_mode in [
                "delegated",
                "cached",
                "consistent",
            ]:
                if consistency_mode in mode_parts:
                    mount_list.append(
                        f"consistency={consistency_mode}"
                    )
                    break
            if mount.propagation:
                mount_list.append(
                    f"bind-propagation={mount.propagation}"
                )

        if type == "volume":
            if mount.name:
                source = mount.name
            driver = mount.driver or "local"
            if driver != "local":
                mount_list.append(f"volume-driver={driver}")
                # TODO add volume driver options
        if source:
            # Source could be emptry e.g. for tmpfs mount
            mount_list.append(f"source={source}")
        docker_mounts.append(mount_list)

    return docker_mounts
