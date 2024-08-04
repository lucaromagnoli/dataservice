from __future__ import annotations

from logging import getLogger

import httpx

from dataservice.models import Request, Response
from exceptions import RequestException, RetryableRequestException

logger = getLogger(__name__)


class HttpXClient:
    """Client that uses HTTPX library to make requests."""

    def __init__(self):
        self.async_client = httpx.AsyncClient

    def __call__(self, *args, **kwargs):
        return self.make_request(*args, **kwargs)

    async def make_request(self, request: Request) -> Response:
        """Make a request and handle exceptions."""
        try:
            return await self._make_request(request)
        except httpx.HTTPStatusError as e:
            logger.debug(f"Request exception making request: {e}")
            if 400 >= e.response.status_code < 500:
                raise RequestException(
                    e.response.text, status_code=e.response.status_code
                )
            elif 500 >= e.response.status_code < 600:
                raise RetryableRequestException(
                    e.response.text, status_code=e.response.status_code
                )
        except httpx.TimeoutException as e:
            logger.debug(f"Timeout exception making request: {e}")
            raise RetryableRequestException(e)
        except httpx.HTTPError as e:
            logger.debug(f"HTTP Error making request: {e}")
            raise RequestException(e)

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
