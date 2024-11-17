"""Clients."""

from __future__ import annotations

import warnings
from abc import ABC
from logging import getLogger
from typing import Annotated, Any, Awaitable, Callable, NoReturn, Optional, Sequence

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
from dataservice.models import (
    CallbackType,
    InterceptRequest,
    InterceptResponse,
    Request,
    Response,
)

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

    async def __call__(
        self, *args, **kwargs
    ) -> Response | Sequence[Response] | NoReturn:
        """Make a request using the client."""
        return await self.make_request(*args, **kwargs)

    async def make_request(
        self, request: Request
    ) -> Response | Sequence[Response] | NoReturn:
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

    async def make_request(self, request: Request) -> Response | NoReturn:
        """Make a request using HTTPX.

        :param request: The request object containing the details of the HTTP request.
        :return: A Response object containing the response data.
        """
        try:
            logger.info(f"Requesting {request.url}")
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
        config: PlaywrightConfig = PlaywrightConfig(),
    ):
        """Initialize the PlaywrightClient.

        :param actions: Optional coroutine with actions to perform on the page before returning the response.
        :param intercept_url: Optional URL to intercept and get data from.
        :param config: PlaywrightConfig object.
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "Playwright optional dependency is not installed. Please install it with `pip install python-dataservice[playwright]`."
            )

        self.actions = actions
        self.intercept_url = intercept_url
        self.config = config
        self._intercepted_requests: list[PlaywrightRequest] = []

        if self.intercept_url:
            warnings.warn(
                "Please consider using PlaywrightInterceptClient to intercept requests. "
                "In future releases, PlaywrightClient will not support intercepting requests."
            )

    def _get_context_kwargs(
        self, request: Request, config: PlaywrightConfig
    ) -> dict[str, Any]:
        """Get the context kwargs for the Playwright client.

        :param request: The request object containing the details of the HTTP request.
        :param config: The Playwright configuration object.
        :return: A dictionary containing the context kwargs.
        """
        context_kwargs = {}

        if request.proxy:
            context_kwargs["proxy"] = {"server": request.proxy.url}
        if request.headers:
            context_kwargs["extra_http_headers"] = request.headers
        if config is not None and config.device:
            context_kwargs.update(config.device)
        return context_kwargs

    async def _set_up(
        self, request: Request, config: PlaywrightConfig
    ) -> tuple[Browser, BrowserContext, PlaywrightPage, Playwright]:
        """Set up the Playwright client.
        :param request: The request object containing the details of the HTTP request.
        :param config: The Playwright configuration object.
        """
        playwright = await async_playwright().start()
        browser = await getattr(playwright, config.browser).launch(
            headless=config.headless
        )
        context_kwargs = self._get_context_kwargs(request, config)
        context = await browser.new_context(**context_kwargs)
        page = await context.new_page()
        return browser, context, page, playwright

    async def _clean_up(self, browser, context, page, playwright):
        """Close the Playwright resources.
        :param browser: The Playwright browser object.
        :param context: The Playwright context object.
        :param page: The Playwright page object.
        :param playwright: The Playwright object.
        """
        await page.close()
        await context.close()
        await browser.close()
        await playwright.stop()

    def _intercept_requests(self, request: PlaywrightRequest):
        """Intercept requests and store the data.

        :param request: The request object to intercept.
        """
        seen = set()
        if self.intercept_url in request.url and request.url not in seen:
            logger.debug(f"Intercepted request: {request.url}")
            seen.add(request.url)
            if self._intercepted_requests:
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
                    content_type = response.headers.get("content-type", "")
                    if "application/json" in content_type:
                        responses[request.url] = await response.json()
                    else:
                        responses[request.url] = await response.text()
        return responses

    async def make_request(self, request: Request) -> Response:
        """Make a request using Playwright without assigning instance variables.
        :param request: The request object containing the details of the HTTP request.
        """
        browser, context, page, playwright = await self._set_up(request, self.config)

        if self.intercept_url is not None:
            page.on("request", lambda pw_request: self._intercept_requests(pw_request))

        try:
            logger.debug(f"Requesting {request.url_encoded}")
            # Playwright page.goto() timeout is in milliseconds
            pw_response = await page.goto(request.url, timeout=request.timeout * 1000)
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
            await self._clean_up(browser, context, page, playwright)


class PlaywrightInterceptClient(PlaywrightClient):
    """Client that uses Playwright library to make requests and intercept responses."""

    def __init__(
        self,
        *,
        intercept_url: str,
        callback: CallbackType,
        return_html: bool = True,
        actions: Optional[Callable[[PlaywrightPage], Awaitable[None]]] = None,
        config: PlaywrightConfig = PlaywrightConfig(),
    ):
        """Initialize the PlaywrightInterceptClient.

        :param intercept_url: The URL to intercept and get data from.
        :param callback: The callback function to process the intercepted response.
        :param return_html: Whether to return the HTML content of the page.
        :param actions: Optional coroutine with actions to perform on the page before returning the response.
        :param config: PlaywrightConfig object.
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "Playwright optional dependency is not installed. Please install it with `pip install python-dataservice[playwright]`."
            )

        super().__init__(actions=actions, config=config)

        self.intercept_url = intercept_url
        self.callback = callback
        self.return_html = return_html
        self._intercepted_requests: list[PlaywrightRequest] = []

    async def make_request(self, request: Request) -> Sequence[Response]:  # type: ignore
        """Make a request and intercept Fetch/XHR responses.

        :param request: The request object containing the details of the HTTP request.
        :return: A list of ResponseObjects.
        :raises RequestException: If a non-retryable HTTP error occurs.
        :raises RetryableRequestException: If a retryable HTTP error occurs.
        """
        browser, context, page, playwright = await self._set_up(request, self.config)
        page.on("request", lambda pw_request: self._intercept_requests(pw_request))
        responses = []
        try:
            logger.debug(f"Requesting {request.url_encoded}")
            # Playwright page.goto() timeout is in milliseconds
            pw_response = await page.goto(request.url, timeout=request.timeout * 1000)
            logger.debug(f"Received response for {request.url_encoded}")
            self._raise_for_status(pw_response.status, pw_response.status_text)

            if self.actions is not None:
                await self.actions(page)

            if self.return_html:
                text = await page.content()
                cookies = await context.cookies()

                html_response = Response(
                    request=request,
                    text=text,
                    data=None,
                    url=HttpUrl(pw_response.url),
                    status_code=pw_response.status,
                    cookies=cookies,
                    headers=pw_response.headers,
                )

                responses.append(html_response)
            for pw_request in self._intercepted_requests:
                pw_response = await pw_request.response()
                data, text = None, ""
                pw_response_headers = pw_response.headers
                content_type = pw_response_headers.get("content-type", "")
                if "application/json" in content_type:
                    data = await pw_response.json()
                else:
                    text = await pw_response.text()
                request = InterceptRequest(
                    parent=request,
                    url=pw_request.url,
                    headers=pw_request.headers,
                    method=pw_request.method,
                    json_data=pw_request.post_data_json,
                    callback=self.callback,
                )
                responses.append(
                    InterceptResponse(
                        request=request,
                        text=text,
                        data=data,
                        url=HttpUrl(pw_response.url),
                        status_code=pw_response.status,
                        headers=pw_response.headers,
                    )
                )
            return responses

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
            await self._clean_up(browser, context, page, playwright)
