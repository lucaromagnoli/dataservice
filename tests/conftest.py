import asyncio
import random

import pytest

from dataservice.client import Client
from dataservice.service import RequestWorker, ResponseWorker
from tests.clients import ToyClient, AnotherToyClient


@pytest.fixture
def clients() -> tuple[Client]:
    return ToyClient(), AnotherToyClient()


@pytest.fixture
def requests_worker(clients):
    return RequestWorker(clients)


@pytest.fixture
def responses_worker():
    return ResponseWorker()
