"""Clients."""

from __future__ import annotations

from logging import getLogger
from typing import Annotated, Any, Awaitable, Callable, Literal, NoReturn, Optional

import httpx
from annotated_types import Ge, Le
from pydantic import HttpUrl

from dataservice.config import PlaywrightConfig
from dataservice.exceptions import (
    DataServiceException,
    NonRetryableException,
    RetryableException,
    TimeoutException,
)
from dataservice.models import Request, Response

try:
    from playwright.async_api import (
        Browser,
        BrowserContext,
        Playwright,
        async_playwright,
    )
    from playwright.async_api import Page as PlaywrightPage
    from playwright.async_api import Request as PlaywrightRequest
    from playwright.async_api import Response as PlaywrightResponse
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    Browser = None
    BrowserContext = None
    Playwright = None
    PlaywrightPage = None
    PlaywrightRequest = None
    PlaywrightResponse = None
    async_playwright = None
    PLAYWRIGHT_AVAILABLE = False

logger = getLogger(__name__)


class HttpXClient:
    """Client that uses HTTPX library to make requests."""

    def __init__(self):
        self.async_client = httpx.AsyncClient

    def __call__(self, *args, **kwargs):
        """Make a request using the client."""
        return self.make_request(*args, **kwargs)

    async def make_request(self, request: Request) -> Response | NoReturn:
        """Make a request and handle exceptions.

        :param request: The request object containing the details of the HTTP request.
        :return: A Response object if the request is successful.
        :raises RequestException: If a non-retryable HTTP error occurs.
        :raises RetryableRequestException: If a retryable HTTP error occurs.
        """
        try:
            return await self._make_request(request)
        except httpx.HTTPStatusError as e:
            logger.debug(f"HTTP Status Error making request: {e}")
            status_code: Annotated[int, Ge(400), Le(600)] = e.response.status_code
            if status_code == 429 or 500 <= status_code < 600:
                raise RetryableException(
                    e.response.reason_phrase, status_code=e.response.status_code
                )
            else:
                raise NonRetryableException(
                    e.response.reason_phrase, status_code=e.response.status_code
                )

        except httpx.TimeoutException as e:
            msg = f"Timeout making request: {e}, {e.__class__.__name__}"
            logger.debug(msg)
            raise TimeoutException(msg)

        except httpx.HTTPError as e:
            msg = f"HTTP Error making request: {e}, {e.__class__.__name__}"
            logger.debug(msg)
            raise DataServiceException(msg)

    async def _make_request(self, request: Request) -> Response:
        """Make a request using HTTPX. Private method for internal use.

        :param request: The request object containing the details of the HTTP request.
        :return: A Response object containing the response data.
        """
        logger.debug(f"Requesting {request.url_encoded}")
        async with self.async_client(
            headers=request.headers,
            proxy=request.proxy.url if request.proxy else None,
            timeout=request.timeout,
            follow_redirects=True,
        ) as client:
            match request.method:
                case "GET":
                    response = await client.get(request.url, params=request.params)
                case "POST":
                    response = await client.post(
                        request.url,
                        params=request.params,
                        data=request.form_data,
                        json=request.json_data,
                    )
            response.raise_for_status()
            match request.content_type:
                case "text":
                    data = None
                case "json":
                    data = response.json()
        msg = f"Received response for {request.url}"
        if request.params:
            msg += f" - params {request.params}"
        if request.form_data:
            msg += f" - form data {request.form_data}"
        if request.json_data:
            msg += f" - json data {request.json_data}"

        logger.debug(msg)
        return Response(
            request=request,
            text=response.text,
            data=data,
            url=HttpUrl(str(response.url)),
            headers=dict(response.headers),
        )


class PlaywrightClient:
    """Client that uses Playwright library to make requests."""

    def __init__(
        self,
        *,
        actions: Optional[Callable[[PlaywrightPage], Awaitable[None]]] = None,
        intercept_url: Optional[str] = None,
        intercept_content_type: Optional[Literal["text", "json"]] = "json",
        config: Optional[PlaywrightConfig] = None,
    ):
        """Initialize the PlaywrightClient.

        :param actions: Optional coroutine with actions to perform on the page before returning the response.
        :param intercept_url: Optional URL to intercept and get data from.
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "Playwright optional dependency is not installed. Please install it with `pip install python-dataservice[playwright]`."
            )

        self.actions = actions
        self.intercept_url = intercept_url
        self.intercept_content_type = intercept_content_type
        self.config = config
        self._intercepted_requests: list[PlaywrightRequest] | None = None
        self.async_playwright = async_playwright
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: PlaywrightPage | None = None

    def __call__(self, *args, **kwargs):
        """Make a request using the client."""
        return self.make_request(*args, **kwargs)

    def _get_context_kwargs(self, request: Request) -> dict[str, Any]:
        """Get the context kwargs for the Playwright client.

        :param request: The request object containing the details of the HTTP request.
        :return: A dictionary containing the context kwargs.
        """
        context_kwargs = {}
        if request.proxy:
            context_kwargs["proxy"] = {"server": request.proxy.url}
        if self.config is not None and self.config.device:
            context_kwargs.update(self.config.device)
        return context_kwargs

    async def make_request(self, request: Request) -> Response | NoReturn:
        """Make a request and handle exceptions.

        :param request: The request object containing the details of the HTTP request.
        :return: A Response object if the request is successful.
        :raises RequestException: If a non-retryable HTTP error occurs.
        :raises RetryableRequestException: If a retryable HTTP error occurs.
        """
        return await self._make_request(request)

    @staticmethod
    def _raise_for_status(response: PlaywrightResponse):
        """Raise an exception if the response status code is not 2xx.

        :param response: The response object to check.
        :raises RetryableException: If the status code is 5xx.
        :raises DataServiceException: If the status code is not 2xx or 5xx.
        """
        if response.status == 200:
            return
        elif 500 <= response.status < 600 or response.status == 429:
            raise RetryableException(response.status_text, status_code=response.status)
        else:
            raise NonRetryableException(
                response.status_text, status_code=response.status
            )

    def _intercept_requests(self, request: PlaywrightRequest):
        """Intercept requests and store the data.

        :param request: The request object to intercept.
        """
        seen = set()
        if self.intercept_url in request.url and request.url not in seen:
            logger.debug(f"Intercepted request: {request.url}")
            seen.add(request.url)
            if self._intercepted_requests is not None:
                self._intercepted_requests.append(request)
            else:
                self._intercepted_requests = [request]

    async def _get_intercepted_requests(self) -> dict[str, dict[str, Any]]:
        """Get the responses from the intercepted requests.

        :return: A dictionary containing the responses from the intercepted requests.
        """
        responses = {}
        if self._intercepted_requests:
            for request in self._intercepted_requests:
                if request.url not in responses:
                    response = await request.response()
                    if self.intercept_content_type == "text":
                        responses[request.url] = await response.text()
                    elif self.intercept_content_type == "json":
                        responses[request.url] = await response.json()
        return responses

    async def _init_browser(self, request: Request) -> PlaywrightPage:
        """Initialize the Playwright browser and context."""
        browser_name = self.config.browser if self.config else "chromium"
        headless = self.config.headless if self.config else True
        self.playwright = await self.async_playwright().start()
        self.browser = await getattr(self.playwright, browser_name).launch(
            headless=headless
        )

        context_kwargs = self._get_context_kwargs(request)
        self.context = await self.browser.new_context(**context_kwargs)

        self.page = await self.context.new_page()
        if self.intercept_url is not None:
            self.page.on(
                "request", lambda pw_request: self._intercept_requests(pw_request)
            )

    async def _make_request(self, request: Request) -> Response:
        """Make a request using Playwright. Private method for internal use.

        :param request: The request object containing the details of the HTTP request.
        :return: A Response object containing the response data.
        """
        await self._init_browser(request)
        logger.debug(f"Requesting {request.url_encoded}")

        if (
            self.page is None
            or self.context is None
            or self.browser is None
            or self.playwright is None
        ):
            raise RuntimeError("Playwright components are not initialized properly")
        try:
            pw_response = await self.page.goto(request.url)
            self._raise_for_status(pw_response)

            if self.actions is not None:
                await self.actions(self.page)

            text = await self.page.content()
            data = None
            logger.debug(f"Received response for {request.url}")

            if self._intercepted_requests:
                data = await self._get_intercepted_requests()

            cookies = await self.context.cookies()
            await self.context.close()
            await self.browser.close()
            await self.playwright.stop()

            return Response(
                request=request,
                text=text,
                data=data,
                url=HttpUrl(pw_response.url),
                status_code=pw_response.status,
                cookies=cookies,
                headers=pw_response.headers,
            )
        except PlaywrightTimeoutError as e:
            raise TimeoutException(
                f"Timeout making request: {e}, {e.__class__.__name__}"
            )
        except (RetryableException, NonRetryableException) as e:
            raise e
        except Exception as e:
            raise DataServiceException(
                f"Error making request: {e}, {e.__class__.__name__}"
            )
