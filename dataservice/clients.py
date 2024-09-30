"""Clients."""

from __future__ import annotations

from logging import getLogger
from typing import Annotated, NoReturn

import httpx
from annotated_types import Ge, Le
from playwright.async_api import async_playwright
from playwright.async_api._generated import Response as PlaywrightResponse
from pydantic import HttpUrl

from dataservice.exceptions import DataServiceException, RetryableException
from dataservice.models import Request, Response

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
            if 400 <= status_code < 500:
                raise DataServiceException(
                    e.response.reason_phrase, status_code=e.response.status_code
                )
            elif 500 <= status_code < 600:
                raise RetryableException(
                    e.response.reason_phrase, status_code=e.response.status_code
                )
            else:
                raise
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

    def __init__(self):
        self.async_playwright = async_playwright

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
        elif 500 <= response.status < 600:
            raise RetryableException(response.status_text, status_code=response.status)
        else:
            raise DataServiceException(
                response.status_text, status_code=response.status
            )

    async def _make_request(self, request: Request) -> Response:
        """Make a request using Playwright. Private method for internal use.

        :param request: The request object containing the details of the HTTP request.
        :return: A Response object containing the response data.
        """
        logger.info(f"Requesting {request.url}")
        async with self.async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            response = await page.goto(request.url)
            self.raise_for_status(response)
            text = await page.content()
            logger.info(f"Received response for {request.url}")
            return Response(
                request=request, text=text, data=None, url=HttpUrl(response.url)
            )
