import pytest
from httpx import HTTPError, HTTPStatusError, TimeoutException
from httpx import Response as HttpXResponse
from pytest_httpx import HTTPXMock

from dataservice.clients import HttpXClient
from dataservice.exceptions import RequestException, RetryableRequestException
from dataservice.models import Request, Response


@pytest.fixture
def httpx_client():
    return HttpXClient()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url, data, text, content_type, expected",
    [
        pytest.param(
            "https://example.com/",
            {"key": "value"},
            None,
            "json",
            {"key": "value"},
            id="JSON response",
        ),
        pytest.param(
            "https://example.com/",
            None,
            "This is a text response",
            "text",
            "This is a text response",
            id="Text response",
        ),
    ],
)
async def test_httpx_client_get_request(
    httpx_mock, httpx_client, url, data, text, content_type, expected
):
    request_url = "https://example.com/?q=test"
    params = {"q": "test"}
    httpx_mock.add_response(url=request_url, json=data, text=text, method="GET")
    request = Request(
        url=url,
        method="GET",
        params=params,
        callback=lambda x: x,
        content_type=content_type,
        client=HttpXClient,
    )
    expected_response = Response(request=request, data=expected)
    response = await httpx_client._make_request(request)
    assert response.data == expected_response.data


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "url, form_data, json_data, content_type, expected",
    [
        pytest.param(
            "https://example.com/",
            {"key": "value"},
            {"json": ["data"]},
            "json",
            {"key": "value"},
            id="JSON response",
        ),
    ],
)
async def test_httpx_client_post_request(
    httpx_mock, httpx_client, url, form_data, json_data, content_type, expected
):
    request_url = "https://example.com/"
    response = {"response": "example"}
    httpx_mock.add_response(url=request_url, json=response, method="POST")
    request = Request(
        url="https://example.com",
        method="POST",
        form_data=form_data,
        json_data=json_data,
        callback=lambda x: x,
        content_type=content_type,
        client=HttpXClient,
    )
    expected_response = Response(request=request, data=response)
    response = await httpx_client._make_request(request)
    assert response.data == expected_response.data


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "client_exception, expected_exception",
    [
        pytest.param(
            HTTPStatusError(
                "Error", request=None, response=HttpXResponse(status_code=404)
            ),
            RequestException,
            id="404",
        ),
        pytest.param(
            HTTPStatusError(
                "Error", request=None, response=HttpXResponse(status_code=500)
            ),
            RetryableRequestException,
            id="505 Retryable",
        ),
        pytest.param(
            TimeoutException("Error"),
            RetryableRequestException,
            id="Timeout Retryable",
        ),
        pytest.param(
            HTTPError("Error"),
            RequestException,
            id="Error. Dont retry",
        ),
    ],
)
async def test_httpx_client_make_request_exceptions(
    httpx_client, httpx_mock: HTTPXMock, client_exception: HTTPError, expected_exception
):
    request = Request(
        url="https://example.com",
        callback=lambda x: x,
        client=HttpXClient,
    )
    httpx_mock.add_exception(exception=client_exception)
    with pytest.raises(expected_exception):
        await httpx_client.make_request(request)
