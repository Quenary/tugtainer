from backend.exception import TugAgentClientError


def test_agent_client_error_str_uses_detail() -> None:
    error = TugAgentClientError(
        "Agent request error",
        "https://agent.example",
        "GET",
        500,
        {"detail": "denied"},
    )
    rendered = str(error)
    assert "Agent request error" in rendered
    assert "denied" in rendered


def test_agent_client_error_str_uses_text_body() -> None:
    error = TugAgentClientError(
        "Agent connection error",
        "https://agent.example",
        "GET",
        502,
        "connection refused",
    )
    assert "connection refused" in str(error)
