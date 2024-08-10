"""Clients."""

from __future__ import annotations

from logging import getLogger
from typing import Annotated, NoReturn

import httpx
from annotated_types import Ge, Le

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
        return Response(request=request, text=response.text, data=data)
