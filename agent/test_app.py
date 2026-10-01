from pytest_mock import MockerFixture

from agent.app import warn_if_agent_secret_missing


def test_warns_when_secret_missing(mocker: MockerFixture):
    mocker.patch("agent.app.Config.AGENT_SECRET", None)
    mocker.patch("agent.app.Config.ALLOW_UNAUTHENTICATED_AGENT", False)
    warning = mocker.patch("agent.app.logging.warning")

    warn_if_agent_secret_missing()

    warning.assert_called_once()
    message = warning.call_args.args[0]
    assert "AGENT_SECRET is not set" in message


def test_silent_when_dev_flag_enabled(mocker: MockerFixture):
    mocker.patch("agent.app.Config.AGENT_SECRET", None)
    mocker.patch("agent.app.Config.ALLOW_UNAUTHENTICATED_AGENT", True)
    warning = mocker.patch("agent.app.logging.warning")

    warn_if_agent_secret_missing()

    warning.assert_not_called()


def test_silent_when_secret_is_set(mocker: MockerFixture):
    mocker.patch("agent.app.Config.AGENT_SECRET", "my-secret")
    mocker.patch("agent.app.Config.ALLOW_UNAUTHENTICATED_AGENT", False)
    warning = mocker.patch("agent.app.logging.warning")

    warn_if_agent_secret_missing()

    warning.assert_not_called()
