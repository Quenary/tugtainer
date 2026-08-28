from datetime import datetime

from python_on_whales.components.container.models import (
    ContainerConfig,
    ContainerHostConfig,
    ContainerInspectResult,
    ContainerState,
)
from python_on_whales.components.image.models import (
    ImageInspectResult,
)

from backend.core.action_result import (
    ContainerActionResult,
    HostActionResult,
)

_NOW = datetime.now()

TEST_NOTIFICATION_CONTAINER = ContainerInspectResult(
    id="35d6d68589ab16a7b06d26513ecae15a7dee2cdb067be5648074c99a39db9fab",
    created=_NOW,
    path="/hello",
    state=ContainerState(
        status="exited",
        running=False,
        paused=False,
        restarting=False,
        oom_killed=False,
        dead=False,
        pid=0,
        exit_code=0,
        error="",
        started_at=_NOW,
        finished_at=_NOW,
    ),
    image="sha256:1b44b5a3e06a9aae883e7bf25e45c100be0bb81a0e01b32de604f3ac44711634",
    name="hello-world",
    platform="linux",
    host_config=ContainerHostConfig(
        network_mode="bridge",
        port_bindings={},
    ),
    config=ContainerConfig(
        hostname="35d6d68589ab",
        image="docker.io/hello-world:latest",
        labels={},
    ),
)

TEST_NOTIFICATION_IMAGE = ImageInspectResult(
    id="sha256:1b44b5a3e06a9aae883e7bf25e45c100be0bb81a0e01b32de604f3ac44711634",
    repo_tags=["hello-world:latest"],
    repo_digests=[
        "hello-world@sha256:f7931603f70e13dbd844253370742c4fc4202d290c80442b2e68706d8f33ce26"
    ],
    comment="buildkit.dockerfile.v0",
    created=_NOW,
    architecture="amd64",
    os="linux",
    size=10072,
    config=ContainerConfig(
        cmd=["/hello"],
    ),
)

TEST_NOTIFICATION_DIGESTS: list[str] = [
    "sha256:f751174c3d8ae54b12575af320a4aa01bb3b6e61ab82aa1e4f8ecac8a079ce61",
]

TEST_NOTIFICATION_ITEMS: list[ContainerActionResult] = [
    ContainerActionResult(
        container=TEST_NOTIFICATION_CONTAINER,
        local_image=None,
        remote_image=None,
        local_digests=[],
        remote_digests=[],
        result=None,
    ),
    ContainerActionResult(
        container=TEST_NOTIFICATION_CONTAINER,
        local_image=TEST_NOTIFICATION_IMAGE,
        remote_image=None,
        local_digests=TEST_NOTIFICATION_DIGESTS,
        remote_digests=[],
        result="not_available",
    ),
    ContainerActionResult(
        container=TEST_NOTIFICATION_CONTAINER,
        local_image=TEST_NOTIFICATION_IMAGE,
        remote_image=TEST_NOTIFICATION_IMAGE,
        local_digests=TEST_NOTIFICATION_DIGESTS,
        remote_digests=TEST_NOTIFICATION_DIGESTS,
        result="updated",
    ),
    ContainerActionResult(
        container=TEST_NOTIFICATION_CONTAINER,
        local_image=TEST_NOTIFICATION_IMAGE,
        remote_image=TEST_NOTIFICATION_IMAGE,
        local_digests=TEST_NOTIFICATION_DIGESTS,
        remote_digests=TEST_NOTIFICATION_DIGESTS,
        result="available",
    ),
    ContainerActionResult(
        container=TEST_NOTIFICATION_CONTAINER,
        local_image=TEST_NOTIFICATION_IMAGE,
        remote_image=TEST_NOTIFICATION_IMAGE,
        local_digests=TEST_NOTIFICATION_DIGESTS,
        remote_digests=TEST_NOTIFICATION_DIGESTS,
        result="available(notified)",
    ),
    ContainerActionResult(
        container=TEST_NOTIFICATION_CONTAINER,
        local_image=TEST_NOTIFICATION_IMAGE,
        remote_image=TEST_NOTIFICATION_IMAGE,
        local_digests=TEST_NOTIFICATION_DIGESTS,
        remote_digests=TEST_NOTIFICATION_DIGESTS,
        result="rolled_back",
    ),
    ContainerActionResult(
        container=TEST_NOTIFICATION_CONTAINER,
        local_image=TEST_NOTIFICATION_IMAGE,
        remote_image=TEST_NOTIFICATION_IMAGE,
        local_digests=TEST_NOTIFICATION_DIGESTS,
        remote_digests=TEST_NOTIFICATION_DIGESTS,
        result="failed",
    ),
]

TEST_NOTIFICATION_PRUNE_RESULT = """
untagged: postgres@sha256:cf2a05fe40887b721e4b3dbac8fd32673c08292dcc8ba6b62b52b7f640433bd0
deleted: sha256:05c1acb89ae44b0bc936fdad9c7bcf32a2300ef1dbab9407bb6dd12eaee1c8c3
deleted: sha256:030dbd4c7f006cf2a8a482f9128f1b3238e5c820bb107aef0a47299e51179e4b        

Total reclaimed space: 1.5GB
"""

TEST_NOTIFICATION_RESULTS: list[HostActionResult] = [
    HostActionResult(
        host_id=1,
        host_name="test_host_1",
        items=TEST_NOTIFICATION_ITEMS,
        prune_result=TEST_NOTIFICATION_PRUNE_RESULT,
    ),
    HostActionResult(
        host_id=2,
        host_name="test_host_2",
        items=TEST_NOTIFICATION_ITEMS,
        prune_result=TEST_NOTIFICATION_PRUNE_RESULT,
    ),
]
