from __future__ import annotations

from logging import getLogger

import httpx

from dataservice.models import Request, Response

logger = getLogger(__name__)


class HttpXClient:
    """Client that uses HTTPX library to make requests."""

    def __init__(self):
        self.async_client = httpx.AsyncClient

    def __call__(self, *args, **kwargs):
        return self.make_request(*args, **kwargs)

    async def make_request(self, request: Request) -> Response:
        try:
            return await self._make_request(request)
        except httpx.HTTPStatusError as e:
            logger.debug(f"Error making request: {e}")
            return Response(
                request=request, data=None, status_code=e.response.status_code
            )

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
