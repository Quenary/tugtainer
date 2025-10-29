class TugException(Exception):
    """Base tugtainer exception"""

    def __init__(self, message: str):
        super().__init__(message)