from agent.config import Config
from shared.runtime import RuntimeClient

RUNTIME_CLIENT = RuntimeClient(timeout=float(Config.DOCKER_TIMEOUT))
