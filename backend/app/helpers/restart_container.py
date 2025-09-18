import docker
import os


def restart():
    client = docker.DockerClient(base_url=f"unix://var/run/docker.sock")

    container_id = os.environ.get("HOSTNAME")
    if not container_id:
        client.close()
        raise Exception("Can't restart container, missing container_id")

    container = client.containers.get(container_id)
    if not container:
        client.close()
        raise Exception(f"Can't restart container, invalid container_id {container_id}")

    container.restart()
    client.close()
