from unittest.mock import AsyncMock

import pytest
from playwright.async_api import Response as PlaywrightResponse
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from dataservice import DataServiceException, RetryableException
from dataservice.clients import PlaywrightClient
from dataservice.config import PlaywrightConfig
from dataservice.exceptions import NonRetryableException, TimeoutException
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


@pytest.fixture
def mock_playwright_timeout(mocker):
    mock_playwright = AsyncMock()
    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_page = AsyncMock()
    mocker.patch("dataservice.clients.async_playwright", return_value=mock_playwright)
    mock_playwright.start.return_value = mock_playwright
    mock_playwright.chromium.launch.return_value = mock_browser
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page
    mock_page.goto.side_effect = PlaywrightTimeoutError("Timeout occurred")
    return mock_playwright, mock_browser, mock_context, mock_page


@pytest.mark.asyncio
async def test_playwright_client_timeout_error(mock_playwright_timeout):
    client = PlaywrightClient()
    request = get_request(client)

    with pytest.raises(TimeoutException) as excinfo:
        await client.make_request(request)

    assert "Timeout making request" in str(excinfo.value)


@pytest.fixture
def mock_playwright_response(mocker):
    mock_response = mocker.create_autospec(PlaywrightResponse, instance=True)
    return mock_response


@pytest.mark.parametrize(
    "status_code, status_text, expected_exception",
    [
        (200, "OK", None),
        (500, "Internal Server Error", RetryableException),
        (404, "Not Found", NonRetryableException),
        (429, "Too Many Requests", RetryableException),
        (503, "Service Unavailable", RetryableException),
        (504, "Gateway Timeout", RetryableException),
    ],
)
def test_raise_for_status(status_code, status_text, expected_exception):
    client = PlaywrightClient()

    if expected_exception:
        with pytest.raises(expected_exception) as excinfo:
            client._raise_for_status(status_code, status_text)
        assert status_text in str(excinfo.value)
    else:
        # Should not raise any exception
        client._raise_for_status(status_code, status_text)
