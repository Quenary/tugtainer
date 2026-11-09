import json

import pytest

from shared.runtime.image_prune import format_image_prune_result, prune_filters


def test_prune_all_sets_dangling_false() -> None:
    assert prune_filters(True, None) == {"dangling": ["false"]}
    assert prune_filters(True, {"label": ["keep"]}) == {
        "label": ["keep"],
        "dangling": ["false"],
    }


def test_default_prune_omits_filters() -> None:
    assert prune_filters(False, None) is None
    assert prune_filters(False, {}) is None
    assert prune_filters(None, {"until": ["24h"]}) == {"until": ["24h"]}


def test_format_counts_untagged_and_deleted_and_ends_with_reclaimed() -> None:
    text = format_image_prune_result(
        {
            "ImagesDeleted": [
                {"Untagged": "nginx:old"},
                {"Deleted": "sha256:abc"},
                {"Untagged": "redis:old", "Deleted": "sha256:def"},
            ],
            "SpaceReclaimed": 1536,
        }
    )
    lines = text.splitlines()
    assert lines[0] == "Deleted Images: 2"
    assert lines[1] == "Untagged Images: 2"
    assert lines[-1] == "Total reclaimed space: 1.5kB"


def test_format_empty_prune() -> None:
    text = format_image_prune_result({})
    assert text.endswith("Total reclaimed space: 0B")


@pytest.mark.parametrize(
    ("size", "expected"),
    [
        (0, "0B"),
        (512, "512B"),
        (1024, "1kB"),
        (1024 * 1024, "1MB"),
        (1536 * 1024 * 1024, "1.5GB"),
    ],
)
def test_human_sizes(size: int, expected: str) -> None:
    text = format_image_prune_result({"SpaceReclaimed": size})
    assert text.endswith(f"Total reclaimed space: {expected}")


def test_filters_are_json_object_for_the_engine() -> None:
    assert json.dumps(prune_filters(True, None)) == '{"dangling": ["false"]}'
