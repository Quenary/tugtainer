from python_on_whales import DockerClient
from agent.config import Config

DOCKER = DockerClient(host=Config.DOCKER_HOST)
