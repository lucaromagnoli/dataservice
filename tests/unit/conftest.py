import asyncio
import logging
import random

import pytest

from dataservice.models import Request, Response

logger = logging.getLogger(__name__)


@pytest.fixture
def toy_client():
    return ToyClient(random_sleep=0)


# @pytest.fixture
# def mock_request():
#     return Request(
#         url="http://example.com",
#         callback=lambda x: {"parsed": "data"},
#         client="ToyClient",
#     )


class ToyClient:
    def __init__(self, random_sleep: int = 0):
        self.random_sleep = random_sleep
        super().__init__()

    def __call__(self, *args, **kwargs):
        return self.make_request(*args, **kwargs)

    async def make_request(self, request: Request) -> Response:
        logger.info(f"Requesting {request.url}")
        block_time = random.randint(0, self.random_sleep) / 100
        await asyncio.sleep(block_time)
        logger.info(
            f"Returning response for {request.url}. Blocked for {block_time} seconds."
        )
        data = f"<html><head></head><body>This is content for URL: {request.url}</body></html>"
        return Response(request=request, data=data)
