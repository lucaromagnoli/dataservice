import asyncio
import random

import pytest

from dataservice.client import Client
from dataservice.messages import Request, Response
from dataservice.workers import RequestsWorker, ResponsesWorker
from tests.clients import ToyClient


@pytest.fixture
def clients() -> tuple[Client]:
    return (ToyClient(),)


@pytest.fixture
def requests_worker(clients):
    return RequestsWorker(clients)


@pytest.fixture
def responses_worker():
    return ResponsesWorker()
