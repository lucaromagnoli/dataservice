import pytest

from dataservice.client import Client
from dataservice.models import Request
from dataservice.service import DataService


@pytest.fixture
def mock_client(mocker):
    client = mocker.MagicMock(spec=Client)
    client.make_request = mocker.AsyncMock(return_value={"data": "response"})
    client.get_name = mocker.Mock(return_value="MockClient")
    return client


@pytest.fixture
def mock_request(mocker):
    r = mocker.MagicMock(spec=Request)
    r.callback = mocker.Mock(return_value={"parsed": "data"})
    r.client = "MockClient"
    return r


@pytest.fixture
def data_service(mock_client, mock_request):
    return DataService(requests=[mock_request], clients=(mock_client,))


@pytest.mark.asyncio
async def test_handles_request_correctly(data_service, mock_request):
    async for result in data_service:
        assert result == {"parsed": "data"}


@pytest.mark.asyncio
async def test_handles_empty_queue(data_service, mock_client):
    data_service = DataService(requests=[], clients=(mock_client,))
    with pytest.raises(ValueError, match="No requests to process"):
        async for _ in data_service:
            pass


import pytest


@pytest.mark.asyncio
async def handles_request_item_puts_dict_in_data_queue(mocker):
    request = mocker.MagicMock()
    request.callback = mocker.MagicMock(return_value={"key": "value"})
    data_service = DataService([], [])
    data_service._handle_request = mocker.AsyncMock(return_value="response")
    await data_service._handle_queue_item(request)
    assert not data_service.__data_queue.empty()
    assert await data_service.__data_queue.get() == {"key": "value"}


@pytest.mark.asyncio
async def handles_request_item_puts_request_in_work_queue(mocker):
    request = mocker.MagicMock()
    request.callback = mocker.MagicMock(return_value=request)
    data_service = DataService([], [])
    data_service._handle_request = mocker.AsyncMock(return_value="response")
    await data_service._handle_queue_item(request)
    assert not data_service.__work_queue.empty()
    assert await data_service.__work_queue.get() == request


@pytest.mark.asyncio
async def handles_request_item_raises_value_error_for_unknown_type(mocker):
    request = mocker.MagicMock()
    request.callback = mocker.MagicMock(return_value=123)
    data_service = DataService([], [])
    data_service._handle_request = mocker.AsyncMock(return_value="response")
    with pytest.raises(ValueError, match="Unknown item type <class 'int'>"):
        await data_service._handle_queue_item(request)


@pytest.mark.asyncio
async def test_processes_generator_requests(data_service, mock_request, mock_client):
    async def generator():
        yield mock_request

    data_service = DataService(requests=generator(), clients=(mock_client,))
    async for result in data_service:
        assert result == {"parsed": "data"}


@pytest.mark.asyncio
async def test_processes_async_generator_requests(
    data_service, mock_request, mock_client
):
    async def async_generator():
        yield mock_request

    data_service = DataService(requests=async_generator(), clients=(mock_client,))
    async for result in data_service:
        assert result == {"parsed": "data"}
