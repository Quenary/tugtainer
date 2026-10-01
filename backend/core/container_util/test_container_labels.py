import pytest
from python_on_whales.components.container.models import (
    ContainerConfig,
    ContainerInspectResult,
)

from backend.const import (
    TUGTAINER_AUTO_CHECK_LABEL,
    TUGTAINER_AUTO_UPDATE_LABEL,
    TUGTAINER_HIDDEN_LABEL,
    TUGTAINER_PROTECTED_LABEL,
)
from backend.core.container_util.container_labels import (
    exclude_hidden_containers,
    get_container_auto_check_label,
    get_container_auto_update_label,
    get_container_hidden_label,
    get_container_protected_label,
    parse_bool_label,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("1", True),
        ("yes", True),
        ("on", True),
        ("false", False),
        ("False", False),
        ("0", False),
        ("no", False),
        ("off", False),
        ("random", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_bool_label(raw, expected):
    assert parse_bool_label(raw) == expected


def test_get_container_auto_check_label():
    assert get_container_auto_check_label(None) is None

    c_none = ContainerInspectResult(
        id="c1",
        config=ContainerConfig(labels={}),
    )
    assert get_container_auto_check_label(c_none) is None

    c_no_config = ContainerInspectResult(id="c1")
    assert get_container_auto_check_label(c_no_config) is None

    c_true = ContainerInspectResult(
        id="c1",
        config=ContainerConfig(labels={TUGTAINER_AUTO_CHECK_LABEL: "true"}),
    )
    assert get_container_auto_check_label(c_true) is True

    c_false = ContainerInspectResult(
        id="c1",
        config=ContainerConfig(labels={TUGTAINER_AUTO_CHECK_LABEL: "false"}),
    )
    assert get_container_auto_check_label(c_false) is False


def test_get_container_auto_update_label():
    assert get_container_auto_update_label(None) is None

    c_none = ContainerInspectResult(
        id="c1",
        config=ContainerConfig(labels={}),
    )
    assert get_container_auto_update_label(c_none) is None

    c_true = ContainerInspectResult(
        id="c1",
        config=ContainerConfig(labels={TUGTAINER_AUTO_UPDATE_LABEL: "true"}),
    )
    assert get_container_auto_update_label(c_true) is True

    c_false = ContainerInspectResult(
        id="c1",
        config=ContainerConfig(labels={TUGTAINER_AUTO_UPDATE_LABEL: "0"}),
    )
    assert get_container_auto_update_label(c_false) is False


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("true", True),
        ("YES", True),
        ("1", True),
        ("on", True),
        ("false", False),
        ("no", False),
        ("maybe", None),
        (None, None),
    ],
)
def test_protected_and_hidden_labels(raw, expected):
    labels = {}
    if raw is not None:
        labels = {
            TUGTAINER_PROTECTED_LABEL: raw,
            TUGTAINER_HIDDEN_LABEL: raw,
        }
    container = ContainerInspectResult(
        id="c1",
        config=ContainerConfig(labels=labels),
    )
    assert get_container_protected_label(container) is expected
    assert get_container_hidden_label(container) is expected


def test_exclude_hidden_containers_keeps_visible():
    visible = ContainerInspectResult(id="v", name="visible")
    hidden = ContainerInspectResult(
        id="h",
        name="hidden",
        config=ContainerConfig(labels={TUGTAINER_HIDDEN_LABEL: "yes"}),
    )
    disabled = ContainerInspectResult(
        id="d",
        name="disabled",
        config=ContainerConfig(labels={TUGTAINER_HIDDEN_LABEL: "false"}),
    )

    assert exclude_hidden_containers([visible, hidden, disabled]) == [
        visible,
        disabled,
    ]
