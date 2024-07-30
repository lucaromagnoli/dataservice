import asyncio

import pytest

from dataservice.client import Client, HTTPXClient
from dataservice.models import Request
from dataservice.service import DataService

@pytest.fixture
def httpx_client():
    return HTTPXClient()

@pytest.fixture
def mock_client(mocker):
    client = mocker.Mock(spec=Client)
    client.make_request = mocker.AsyncMock(return_value={"data": "response"})
    return client

@pytest.fixture
def mock_request(mocker):
    return Request(
        url="http://example.com", callback=mocker.Mock(return_value={"parsed": "data"})
    )

@pytest.fixture
def start_requests(mock_request):
    requests = []
    for _ in range(2):
        requests.append(mock_request)
    return requests


@pytest.fixture
def data_service(mock_client, start_requests):
    return DataService(start_requests=start_requests, clients=(mock_client,))


@pytest.fixture
def data_service_mock_queue(data_service, mocker):
    data_service._queue = mocker.Mock(spec=asyncio.Queue)
    return data_service


