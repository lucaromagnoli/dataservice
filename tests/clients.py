import asyncio
import random

from dataservice.client import Client
from dataservice.models import Request, Response


class ToyClient(Client):
    def __init__(self, random_sleep: int = 0):
        self.random_sleep = random_sleep
        super().__init__()

    async def make_request(self, request: Request) -> Response:
        self.logger.info(f"Requesting {request.url}")
        block_time = random.randint(0, self.random_sleep) / 100
        await asyncio.sleep(block_time)
        self.logger.info(
            f"Returning response for {request.url}. Blocked for {block_time} seconds."
        )
        data = f"<html><head></head><body>This is content for URL: {request.url}</body></html>"
        return Response(request=request, form_data=data)


class AnotherToyClient(Client):
    async def make_request(self, request: Request) -> Response:
        data = f"<html><head></head><body>This is content for URL: {request.url}</body></html>"
        return Response(request=request, form_data=data)
