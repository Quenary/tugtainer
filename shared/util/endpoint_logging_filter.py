import logging


class EndpointLoggingFilter(logging.Filter):
    def __init__(self, exclude: list[str]):
        self._exclude = exclude

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        return not any(
            endpoint in message for endpoint in self._exclude
        )
