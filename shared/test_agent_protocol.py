from shared.agent_protocol import (
    AGENT_PROTOCOL,
    AGENT_UPGRADE_MESSAGE,
    protocol_error,
    read_installed_version,
)


def test_protocol_constant_is_2() -> None:
    assert AGENT_PROTOCOL == 2
    assert protocol_error(2) is None
    assert protocol_error(1) == AGENT_UPGRADE_MESSAGE
    assert protocol_error(None) == AGENT_UPGRADE_MESSAGE


def test_missing_version_file_is_dev(tmp_path) -> None:
    assert read_installed_version(str(tmp_path / "missing")) == "dev"


def test_version_file_is_stripped(tmp_path) -> None:
    path = tmp_path / "version"
    path.write_text("v2.0.0\n")
    assert read_installed_version(str(path)) == "v2.0.0"
