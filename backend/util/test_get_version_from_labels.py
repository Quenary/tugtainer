import pytest

from backend.util.get_version_from_labels import get_version_from_labels


@pytest.mark.parametrize(
    ("labels", "expected"),
    [
        ({"org.opencontainers.image.version": "1.2.3"}, "1.2.3"),
        ({"org.label-schema.version": "1.2.3"}, "1.2.3"),
        (
            {
                "org.label-schema.version": "0.9.0",
                "org.opencontainers.image.version": "1.2.3",
            },
            "1.2.3",
        ),
        ({"org.opencontainers.image.version": "  1.2.3\n"}, "1.2.3"),
        ({"org.opencontainers.image.version": "   "}, None),
        ({}, None),
        (None, None),
    ],
)
def test_get_version_from_labels(
    labels: dict[str, str] | None, expected: str | None
) -> None:
    assert get_version_from_labels(labels) == expected
