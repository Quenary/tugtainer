from backend.util.get_version_from_labels import get_version_from_labels


def test_version_label_from_oci_label():
    assert (
        get_version_from_labels({"org.opencontainers.image.version": "1.2.3"})
        == "1.2.3"
    )


def test_version_label_falls_back_to_label_schema():
    assert get_version_from_labels({"org.label-schema.version": "1.2.3"}) == "1.2.3"


def test_version_label_prefers_oci_over_label_schema():
    assert (
        get_version_from_labels(
            {
                "org.label-schema.version": "0.9.0",
                "org.opencontainers.image.version": "1.2.3",
            }
        )
        == "1.2.3"
    )


def test_version_label_is_stripped():
    assert (
        get_version_from_labels({"org.opencontainers.image.version": "  1.2.3\n"})
        == "1.2.3"
    )


def test_version_label_ignores_blank_value():
    assert get_version_from_labels({"org.opencontainers.image.version": "   "}) is None


def test_version_label_without_labels():
    assert get_version_from_labels({}) is None
    assert get_version_from_labels(None) is None
