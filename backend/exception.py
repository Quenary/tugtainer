from typing import Any


class TugException(Exception):
    """Base tugtainer exception"""

    def __init__(self, message: str):
        super().__init__(message)


class TugNoAuthProviderException(TugException):
    """Exception for cases when no auth provider is enabled or found"""

    def __init__(
        self,
        message: str = "Authentication providers not found.",
    ):
        super().__init__(message)


class TugAgentClientError(TugException):
    """
    Exception for agent client errors
    :param message: message
    :param url: url of the request
    :param method: method of the request
    :param status: status code
    :param body: body of the request error (json or text)
    """

    def __init__(
        self,
        message: str,
        url: str,
        method: str,
        status: int,
        body: Any,
    ):
        super().__init__(message)
        self.message = message
        self.url = url
        self.method = method
        self.status = status
        self.body = body

    def __str__(self) -> str:
        res = f"{self.message}\n{self.url}\n{self.method}\n{self.status}\n"
        if isinstance(self.body, dict) and (
            _d := self.body.get("detail")
        ):
            res += f"\n{_d}"
        elif isinstance(self.body, str):
            res += f"\n{self.body}"
        return res
