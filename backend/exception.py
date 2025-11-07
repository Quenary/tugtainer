class TugException(Exception):
    """Base tugtainer exception"""

    def __init__(self, message: str):
        super().__init__(message)


class TugNoAuthProviderException(TugException):
    """Exception for cases when no auth provider is enabled"""

    def __init__(
        self,
        message: str = "No active authentication providers found.",
    ):
        super().__init__(message)
