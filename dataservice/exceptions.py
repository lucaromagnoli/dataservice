class DataServiceException(Exception):
    """Base class for all DataService exceptions."""


class RequestException(DataServiceException):
    """Base class for all Request exceptions."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


class RetryableRequestException(RequestException):
    """Base class for all retriable Request exceptions."""
