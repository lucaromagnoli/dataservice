import asyncio
import random

from dataservice.http import Request, Response


class Client:
    async def make_request(self, request: Request) -> Response:
        await asyncio.sleep(random.randint(0, 200) / 100)
        print(f"Requesting {request}")
        return Response(request=request, data="response data")
