import asyncio
import random
from logging import getLogger

from dataservice.messages import Request, Response


class Client:
    def __init__(self):
        self.logger = getLogger(__name__)

    def get_name(self):
        return self.__class__.__name__

    async def make_request(self, request: Request) -> Response:
        raise NotImplementedError


class ToyClient(Client):
    async def make_request(self, request: Request) -> Response:
        self.logger.info(f"Requesting {request.url}")
        await asyncio.sleep(random.randint(0, 200) / 100)
        self.logger.info(f"Returning response for {request.url}")
        data = f"<html><head></head><body>This is content for URL: {request.url}</body></html>"
        return Response(request=request, data=data)
