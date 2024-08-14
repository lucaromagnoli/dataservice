"""Exceptions module."""


class DataServiceException(Exception):
    """Base class for all DataService exceptions."""

    def __init__(self, message: str, status_code: int | None = None):
        """Initialize the DataService.
        :param message: The message to display.
        :param status_code: The status code of the response if there is one
        """
        self.status_code = status_code
        super().__init__(message)


class ParsingException(DataServiceException):
    """Exception raised when parsing fails."""


class RetryableException(DataServiceException):
    """Base class for all retryable exceptions."""
