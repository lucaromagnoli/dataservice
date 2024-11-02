"""Clients."""

from __future__ import annotations

from logging import getLogger
from typing import Annotated, Any, Awaitable, Callable, NoReturn, Optional

import httpx
from annotated_types import Ge, Le
from pydantic import HttpUrl

from dataservice.exceptions import DataServiceException, RetryableException
from dataservice.models import Request, Response

try:
    from playwright.async_api import Page as PlaywrightPage
    from playwright.async_api import Request as PlaywrightRequest
    from playwright.async_api import Response as PlaywrightResponse
    from playwright.async_api import async_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
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
                raise DataServiceException(
                    e.response.reason_phrase, status_code=e.response.status_code
                )
        except httpx.HTTPError as e:
            msg = f"HTTP Error making request: {e}, {e.__class__.__name__}"
            logger.debug(msg)
            raise DataServiceException(msg)

    async def _make_request(self, request: Request) -> Response:
        """Make a request using HTTPX. Private method for internal use.

        :param request: The request object containing the details of the HTTP request.
        :return: A Response object containing the response data.
        """
        logger.info(f"Requesting {request.url}")
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

        logger.info(msg)
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
        actions: Optional[Callable[[PlaywrightPage], Awaitable[None]]] = None,
        intercept_url: Optional[str] = None,
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
        self.async_playwright = async_playwright
        self._intercepted_requests: list[PlaywrightRequest] | None = None

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
        return await self._make_request(request)

    @staticmethod
    def raise_for_status(response: PlaywrightResponse):
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
            raise DataServiceException(
                response.status_text, status_code=response.status
            )

    def _intercept_requests(self, request: PlaywrightRequest):
        """Intercept requests and store the data.

        :param request: The request object to intercept.
        """
        seen = set()
        if self.intercept_url in request.url and request.url not in seen:
            logger.info(f"Intercepted request: {request.url}")
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
                    responses[request.url] = await response.json()
        return responses

    async def _make_request(self, request: Request) -> Response:
        """Make a request using Playwright. Private method for internal use.

        :param request: The request object containing the details of the HTTP request.
        :return: A Response object containing the response data.
        """
        logger.info(f"Requesting {request.url}")
        async with self.async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context()
            page = await context.new_page()
            if self.intercept_url is not None:
                page.on(
                    "request", lambda pw_request: self._intercept_requests(pw_request)
                )
            pw_response = await page.goto(request.url)
            self.raise_for_status(pw_response)
            if self.actions is not None:
                await self.actions(page)

            text = await page.content()
            data = None
            logger.info(f"Received response for {request.url}")

            if self._intercepted_requests:
                data = await self._get_intercepted_requests()

            cookies = await context.cookies()
            await context.close()
            await browser.close()

            return Response(
                request=request,
                text=text,
                data=data,
                url=HttpUrl(pw_response.url),
                status_code=pw_response.status,
                cookies=cookies,
                headers=pw_response.headers,
            )
