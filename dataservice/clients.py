"""Clients."""

from __future__ import annotations

from abc import ABC
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


class BaseClient(ABC):
    """Base client class."""

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
        logger.debug(f"Requesting {request.url_encoded}")
        return await self._make_request(request)

    async def _make_request(self, request: Request) -> Response | NoReturn:
        """Make a request using the client. Private method for internal use."""
        raise NotImplementedError

    @staticmethod
    def _raise_for_status(status_code: int, status_text: str):
        """Raise an exception if the response status code is not 2xx.

        :param status_code: The status code of the response.
        :param status_text: The status text of the response.
        :raises RetryableException: If the status code is 5xx.
        :raises DataServiceException: If the status code is not 2xx or 5xx.
        """
        if status_code == 200:
            return
        elif 500 <= status_code < 600 or status_code in [429, 403]:
            raise RetryableException(status_text, status_code=status_code)
        else:
            raise NonRetryableException(status_text, status_code=status_code)


class HttpXClient(BaseClient):
    """Client that uses HTTPX library to make requests."""

    def __init__(self):
        self.async_client = httpx.AsyncClient

    async def _make_request(self, request: Request) -> Response | NoReturn:
        """Make a request using HTTPX. Private method for internal use.

        :param request: The request object containing the details of the HTTP request.
        :return: A Response object containing the response data.
        """
        try:
            return await self._get_response(request)
        except httpx.HTTPStatusError as e:
            logger.debug(f"HTTP Status Error making request: {e}")
            status_code: Annotated[int, Ge(400), Le(600)] = e.response.status_code
            self._raise_for_status(status_code, e.response.reason_phrase)

        except httpx.TimeoutException as e:
            msg = f"Timeout making request: {e}, {e.__class__.__name__}"
            logger.debug(msg)
            raise TimeoutException(msg)

        except httpx.HTTPError as e:
            msg = f"HTTP Error making request: {e}, {e.__class__.__name__}"
            logger.debug(msg)
            raise DataServiceException(msg)

        assert False, "Should not reach this point"

    async def _get_response(self, request) -> Response:
        """Get the response from the request.
        :param request: The request object containing the details of the HTTP request.
        :return: A Response object containing the response data.
        """
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


class PlaywrightClient(BaseClient):
    """Client that uses Playwright library to make requests."""

    def __init__(
        self,
        *,
        actions: Optional[Callable[[PlaywrightPage], Awaitable[None]]] = None,
        intercept_url: Optional[str] = None,
        intercept_content_type: Optional[Literal["text", "json"]] = "json",
        config: PlaywrightConfig = PlaywrightConfig(),
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

    def _get_context_kwargs(self, request: Request) -> dict[str, Any]:
        """Get the context kwargs for the Playwright client.

        :param request: The request object containing the details of the HTTP request.
        :return: A dictionary containing the context kwargs.
        """
        context_kwargs = {}
        if request.proxy:
            context_kwargs["proxy"] = {"server": request.proxy.url}
        if request.headers:
            context_kwargs["extra_http_headers"] = request.headers
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

    async def _setup(
        self, request: Request
    ) -> tuple[Browser, BrowserContext, PlaywrightPage, Playwright]:
        """Set up the Playwright client."""
        playwright = await async_playwright().start()
        browser = await getattr(playwright, self.config.browser).launch(
            headless=self.config.headless
        )
        context_kwargs = self._get_context_kwargs(request)
        context = await browser.new_context(**context_kwargs)
        page = await context.new_page()
        return browser, context, page, playwright

    async def _make_request(self, request: Request) -> Response:
        """Make a request using Playwright without assigning instance variables."""
        browser, context, page, playwright = await self._setup(request)

        if self.intercept_url is not None:
            page.on("request", lambda pw_request: self._intercept_requests(pw_request))

        try:
            logger.debug(f"Requesting {request.url_encoded}")
            pw_response = await page.goto(request.url)
            logger.debug(f"Received response for {request.url_encoded}")
            self._raise_for_status(pw_response.status, pw_response.status_text)

            if self.actions is not None:
                await self.actions(page)

            text = await page.content()
            data = (
                await self._get_intercepted_requests()
                if self._intercepted_requests
                else None
            )
            cookies = await context.cookies()

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
            logger.debug(f"Timeout making request: {e}")
            raise TimeoutException(
                f"Timeout making request: {e}, {e.__class__.__name__}"
            )
        except (RetryableException, NonRetryableException) as e:
            raise e
        except Exception as e:
            raise DataServiceException(
                f"Error making request: {e}, {e.__class__.__name__}"
            )

        finally:
            # Close resources
            await page.close()
            await context.close()
            await browser.close()
            await playwright.stop()
