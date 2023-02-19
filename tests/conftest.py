import asyncio
import random

import pytest

from dataservice.client import Client
from dataservice.messages import Request, Response
from dataservice.workers import RequestsWorker, ResponsesWorker


class ToyClient(Client):
    async def make_request(self, request: Request) -> Response:
        data = f"<html><head></head><body>This is content for URL: {request.url}</body></html>"
        return Response(request=request, data=data)


@pytest.fixture
def clients() -> tuple[Client]:
    return ToyClient(),

@pytest.fixture
def requests_worker(clients):
    return RequestsWorker(clients)


@pytest.fixture
def responses_worker():
    return ResponsesWorker()
