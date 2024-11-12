import pytest

from dataservice.clients import BaseClient
from dataservice.exceptions import NonRetryableException, RetryableException


@pytest.mark.parametrize(
    "status_code, status_text, expected_exception",
    [
        (200, "OK", None),
        (500, "Internal Server Error", RetryableException),
        (503, "Service Unavailable", RetryableException),
        (429, "Too Many Requests", RetryableException),
        (403, "Forbidden", RetryableException),
        (404, "Not Found", NonRetryableException),
        (400, "Bad Request", NonRetryableException),
    ],
)
def test_raise_for_status(status_code, status_text, expected_exception):
    if expected_exception:
        with pytest.raises(expected_exception):
            BaseClient._raise_for_status(status_code, status_text)
    else:
        BaseClient._raise_for_status(status_code, status_text)
