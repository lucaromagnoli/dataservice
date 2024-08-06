class DataServiceException(Exception):
    """Base class for all DataService exceptions."""


class RequestException(DataServiceException):
    """Base class for all Request exceptions."""

    def __init__(self, message: str, status_code: int | None = None):
        """Initialize the RequestException.
        :param message: The message to display.
        :param status_code: The status code of the response
        """
        self.status_code = status_code
        super().__init__(message)


class ParsingException(DataServiceException):
    """Exception raised when parsing fails."""


class RetryableRequestException(RequestException):
    """Base class for all retriable Request exceptions."""
