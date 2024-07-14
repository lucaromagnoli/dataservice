import asyncio

import pytest

from dataservice.client import Client
from dataservice.models import Request
from dataservice.service import DataService


@pytest.fixture
def mock_client(mocker):
    client = mocker.Mock(spec=Client)
    client.make_request = mocker.AsyncMock(return_value={"data": "response"})
    return client


@pytest.fixture
def data_service(mock_client, mocker):
    ds = DataService(clients=(mock_client,))
    ds.queue = mocker.Mock(spec=asyncio.Queue)
    return ds


@pytest.fixture
def mock_request(mocker):
    return Request(
        url="http://example.com", callback=mocker.Mock(return_value={"parsed": "data"})
    )
