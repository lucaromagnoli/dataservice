from __future__ import annotations

from logging import getLogger
from typing import NoReturn, Annotated

import httpx
from annotated_types import Ge, Le

from dataservice.exceptions import RequestException, RetryableRequestException

from dataservice.models import Request, Response

logger = getLogger(__name__)


class HttpXClient:
    """Client that uses HTTPX library to make requests."""

    def __init__(self):
        self.async_client = httpx.AsyncClient

    def __call__(self, *args, **kwargs):
        return self.make_request(*args, **kwargs)

    async def make_request(self, request: Request) -> Response | NoReturn:
        """Make a request and handle exceptions."""
        try:
            return await self._make_request(request)
        except httpx.HTTPStatusError as e:
            logger.debug(f"Request exception making request: {e}")
            status_code: Annotated[int, Ge(400), Le(600)] = e.response.status_code
            if 400 <= status_code < 500:
                raise RequestException(
                    e.response.reason_phrase, status_code=e.response.status_code
                )
            elif 500 <= status_code < 600:
                raise RetryableRequestException(
                    e.response.reason_phrase, status_code=e.response.status_code
                )
            else:
                raise
        except httpx.TimeoutException as e:
            logger.debug(f"Timeout exception making request: {e}")
            raise RetryableRequestException(str(e))
        except httpx.HTTPError as e:
            logger.debug(f"HTTP Error making request: {e}")
            raise RequestException(str(e))

    async def _make_request(self, request: Request) -> Response:
        """Make a request using HTTPX."""
        logger.info(f"Requesting {request.url}")
        async with self.async_client(headers=request.headers) as client:
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
                    data = response.text
                case "json":
                    data = response.json()
        logger.info(f"Returning response for {request.url}")
        return Response(request=request, data=data)
