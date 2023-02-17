import asyncio
import random
from logging import getLogger

from dataservice.http import Request, Response
from dataservice.logger import DataServiceLoggerAdapter

logger = getLogger(__name__)


class Client:
    def __init__(self):
        self.logger = DataServiceLoggerAdapter(
            logger, {"module": self.__class__.__name__}
        )

    async def make_request(self, request: Request) -> Response:
        self.logger.info(f"Requesting {request.url}")
        await asyncio.sleep(random.randint(0, 200) / 100)
        self.logger.info(f"Returning response for {request.url}")
        return Response(request=request, data="response data")
