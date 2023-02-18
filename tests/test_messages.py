from contextlib import nullcontext as should_not_raise

import pytest
from pydantic import ValidationError

from dataservice.messages import Request, Response


@pytest.mark.parametrize(
    "url, context",
    [
        pytest.param(
            "https://www.testurl.com",
            should_not_raise(),
            id="Valid URL. No exception expected.",
        ),
        pytest.param(
            "testurl.com",
            pytest.raises(ValidationError),
            id="Non valid URL. Validation Error expected",
        ),
    ],
)
def test_request_model_url(url, context):
    with context:
        Request(url=url, callback=lambda x: x)


@pytest.mark.parametrize(
    "request_obj, response_data",
    [
        pytest.param(
            Request(url="https://www.testurl.com", callback=lambda x: x),
            "<html><head></head><body>Test</body></html>",
        ),
    ],
)
def test_response_soup(request_obj, response_data):
    response = Response(request=request_obj, data=response_data)
    assert response.soup.text == "Test"
