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
def mock_browser_200_page(mock_browser):
    mock_page = AsyncMock()
    mock_response = AsyncMock()
    mock_browser.new_page.return_value = mock_page
    mock_page.goto.return_value = mock_response
    mock_page.content.return_value = "<html></html>"
    mock_response.status = 200
    mock_response.url = "http://example.com"
    return "<html></html>"


@pytest.fixture
def mock_browser_404_page(mock_browser):
    mock_page = AsyncMock()
    mock_response = AsyncMock()
    mock_browser.new_page.return_value = mock_page
    mock_page.goto.return_value = mock_response
    mock_page.content.return_value = "<html></html>"
    mock_response.status = 404
    mock_response.url = "http://example.com"
    return "<html></html>"


@pytest.fixture
def mock_browser_500_page(mock_browser):
    mock_page = AsyncMock()
    mock_response = AsyncMock()
    mock_browser.new_page.return_value = mock_page
    mock_page.goto.return_value = mock_response
    mock_page.content.return_value = "<html></html>"
    mock_response.status = 500
    mock_response.url = "http://example.com"
    return "<html></html>"


@pytest.fixture
def mock_browser_429_page(mock_browser):
    mock_page = AsyncMock()
    mock_response = AsyncMock()
    mock_browser.new_page.return_value = mock_page
    mock_page.goto.return_value = mock_response
    mock_page.content.return_value = "<html></html>"
    mock_response.status = 429
    mock_response.url = "http://example.com"
    return "<html></html>"


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
async def test_make_request_200(mock_browser_200_page):
    client = PlaywrightClient()
    request = get_request(client)

    response = await client.make_request(request)

    # Assert the response
    assert isinstance(response, Response)
    assert response.text == "<html></html>"
    assert response.url == "http://example.com/"
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_make_request_404(mock_browser_404_page):
    client = PlaywrightClient()
    request = get_request(client)

    with pytest.raises(DataServiceException):
        await client.make_request(request)


@pytest.mark.asyncio
async def test_make_request_retryable_500(mock_browser_500_page):
    client = PlaywrightClient()
    request = get_request(client)

    with pytest.raises(RetryableException):
        await client.make_request(request)


@pytest.mark.asyncio
async def test_make_request_retryable_429(mock_browser_429_page):
    client = PlaywrightClient()
    request = get_request(client)

    with pytest.raises(RetryableException):
        await client.make_request(request)
