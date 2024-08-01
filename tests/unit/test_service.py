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


# @pytest.mark.asyncio
# async def test_handles_invalid_item_type(data_service, mock_client):
#     data_service = DataService(requests=[1,2,3], clients=(mock_client,))
#     with pytest.raises(ValueError, match="Unknown item type"):
#         async for _ in data_service:
#             pass


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
