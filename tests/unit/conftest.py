import asyncio

import pytest

from dataservice import DataService, Request
from tests.unit.clients import ToyClient


@pytest.fixture
def toy_client():
    return ToyClient(random_sleep=0)




@pytest.fixture
def mock_request():
    return Request(
        url="http://example.com",
        callback=lambda x: {"parsed": "data"},
        client="ToyClient",
    )
