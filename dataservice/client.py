import asyncio
import random
from logging import getLogger

from dataservice.http import Request, Response

logger = getLogger(__name__)

class Client:
    async def make_request(self, request: Request) -> Response:
        await asyncio.sleep(random.randint(0, 200) / 100)
        logger.info(f"Requesting {request.url}")
        return Response(request=request, data="response data")
