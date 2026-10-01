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


@pytest.mark.parametrize(
    "getter",
    [get_container_auto_check_label, get_container_auto_update_label],
)
def test_auto_label_missing(getter):
    assert getter(None) is None
    assert getter(ContainerInspectResult(id="c1")) is None
    assert (
        getter(ContainerInspectResult(id="c1", config=ContainerConfig(labels={})))
        is None
    )


@pytest.mark.parametrize(
    ("getter", "label", "raw", "expected"),
    [
        (get_container_auto_check_label, TUGTAINER_AUTO_CHECK_LABEL, "true", True),
        (get_container_auto_check_label, TUGTAINER_AUTO_CHECK_LABEL, "false", False),
        (get_container_auto_update_label, TUGTAINER_AUTO_UPDATE_LABEL, "true", True),
        (get_container_auto_update_label, TUGTAINER_AUTO_UPDATE_LABEL, "0", False),
    ],
)
def test_auto_label_value(getter, label: str, raw: str, expected: bool):
    container = ContainerInspectResult(
        id="c1",
        config=ContainerConfig(labels={label: raw}),
    )
    assert getter(container) is expected


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
