from unittest.mock import AsyncMock

import pytest

from dataservice import DataServiceException, RetryableException
from dataservice.clients import PlaywrightClient
from dataservice.config import PlaywrightConfig
from dataservice.models import Request, Response


@pytest.fixture
def mock_browser(mocker):
    mock_playwright = AsyncMock()
    mock_browser_ = AsyncMock()
    mocker.patch("dataservice.clients.async_playwright", return_value=mock_playwright)
    mock_playwright.start.return_value = mock_playwright
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
    return mock_page


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


@pytest.fixture
def mock_playwright(mocker, request):
    mock_playwright = AsyncMock()
    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_page = AsyncMock()
    mocker.patch("dataservice.clients.async_playwright", return_value=mock_playwright)
    mock_playwright.start.return_value = mock_playwright
    browser_name = request.param
    getattr(mock_playwright, browser_name).launch.return_value = mock_browser
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page
    return mock_playwright, mock_browser, mock_context, mock_page, browser_name


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mock_playwright", ["chromium", "firefox", "webkit"], indirect=True
)
async def test_init_browser(mock_playwright):
    mock_playwright, mock_browser, mock_context, mock_page, browser_name = (
        mock_playwright
    )
    config = PlaywrightConfig(browser=browser_name, headless=True)
    client = PlaywrightClient(config=config)
    request = Request(
        url="http://example.com", method="GET", callback=lambda x: x, client=client
    )

    await client._init_browser(request)

    # Assert that the browser, context, and page are initialized correctly
    assert client.browser == mock_browser
    assert client.context == mock_context
    assert client.page == mock_page
    mock_playwright.start.assert_called_once()
    getattr(mock_playwright, browser_name).launch.assert_called_once_with(headless=True)
    mock_browser.new_context.assert_called_once()
    mock_context.new_page.assert_called_once()
