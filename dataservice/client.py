import asyncio
import random
from abc import ABC, abstractmethod
from logging import getLogger

import httpx

from dataservice.messages import Request, Response


class Client(ABC):
    def __init__(self):
        self.logger = getLogger(__name__)

    def get_name(self):
        return self.__class__.__name__

    @abstractmethod
    async def make_request(self, request: Request) -> Response:
        raise NotImplementedError


class HTTPXClient(Client):
    def __init__(self):
        super().__init__()
        self.async_client = httpx.AsyncClient

    async def make_request(self, request: Request) -> Response:
        self.logger.info(f"Requesting {request.url}")
        async with self.async_client() as client:
            response = await client.get(request.url)
            response.raise_for_status()
            match request.content_type:
                case "text":
                    data = response.text
                case "json":
                    data = response.json()
        self.logger.info(f"Returning response for {request.url}")
        return Response(request=request, data=data)
