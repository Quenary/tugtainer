class TugException(Exception):
    """Base tugtainer exception"""

    def __init__(self, message: str):
        super().__init__(message)


class TugHealthcheckException(TugException):
    """Tugtainer exception for failed  healthcheck after container recreation"""

    pass


class TugAsyncallNoLoopException(TugException):
    """Exception raised  by asyncall function if loop is missing"""
