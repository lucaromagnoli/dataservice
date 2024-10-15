from unittest.mock import AsyncMock

import pytest

from dataservice import DataServiceException, RetryableException
from dataservice.clients import PlaywrightClient
from dataservice.models import Request, Response


@pytest.fixture
def mock_browser(mocker):
    mock_playwright = AsyncMock()
    mock_browser_ = AsyncMock()
    mocker.patch("dataservice.clients.async_playwright", return_value=mock_playwright)
    mock_playwright.__aenter__.return_value = mock_playwright
    mock_playwright.chromium.launch.return_value = mock_browser_
    return mock_browser_


@pytest.fixture
def mock_browser_page(mock_browser, request):
    mock_page = AsyncMock()
    mock_response = AsyncMock()
    mock_context = AsyncMock()
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page
    mock_page.goto.return_value = mock_response
    mock_page.content.return_value = "<html></html>"
    mock_response.status = request.param
    mock_response.url = "http://example.com"
    mock_response.headers = {}
    return mock_response


def get_request(client):
    return Request(
        url="http://example.com",
        method="GET",
        headers={},
        params={},
        form_data=None,
        json_data=None,
        content_type="text",
        proxy=None,
        timeout=30,
        callback=lambda x: x,
        client=client,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("mock_browser_page", [200], indirect=True)
async def test_make_request_200(mock_browser_page):
    client = PlaywrightClient()
    request = get_request(client)

    response = await client.make_request(request)

    # Assert the response
    assert isinstance(response, Response)
    assert response.text == "<html></html>"
    assert response.url == "http://example.com/"
    assert response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize("mock_browser_page", [404], indirect=True)
async def test_make_request_exception(mock_browser_page):
    client = PlaywrightClient()
    request = get_request(client)

    with pytest.raises(DataServiceException):
        await client.make_request(request)


@pytest.mark.asyncio
@pytest.mark.parametrize("mock_browser_page", [429, 503], indirect=True)
async def test_make_request_retryable(mock_browser_page):
    client = PlaywrightClient()
    request = get_request(client)

    with pytest.raises(RetryableException):
        await client.make_request(request)
