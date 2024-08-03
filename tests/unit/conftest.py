import asyncio

import pytest

from dataservice.ab_client import ABClient
from dataservice.models import Request
from dataservice.service import DataService
from tests.unit.clients import ToyClient


@pytest.fixture
def toy_client(mocker):
    return ToyClient(random_sleep=0)


@pytest.fixture
def mock_client(mocker):
    client = mocker.Mock(spec=ABClient)
    client.make_request = mocker.AsyncMock(return_value={"data": "response"})
    return client


@pytest.fixture
def data_service(mock_client, mocker):
    ds = DataService(clients=(mock_client,))
    ds.__queue = mocker.Mock(spec=asyncio.Queue)
    return ds


@pytest.fixture
def mock_request():
    return Request(
        url="http://example.com",
        callback=lambda x: {"parsed": "data"},
        client="ToyClient",
    )
