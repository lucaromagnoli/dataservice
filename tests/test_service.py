import pytest

from models import Request


@pytest.mark.asyncio
async def test_handle_queue_item(data_service, mock_request):
    response = await data_service.handle_queue_item(mock_request)
    assert response == {"parsed": "data"}
    mock_request.callback.assert_called_once()


@pytest.mark.asyncio
async def test_get_batch_items_from_queue(data_service, mock_request):
    await data_service.queue.put(mock_request)
    await data_service.queue.put(mock_request)

    items = await data_service.get_batch_items_from_queue(1)
    assert len(items) == 1
    items = await data_service.get_batch_items_from_queue(1)
    assert len(items) == 1


@pytest.mark.asyncio
async def test_fetch(data_service, mock_request, mocker):
    requests_iterable = [mock_request, mock_request]

    data_service.client.make_request = mocker.AsyncMock(
        return_value={"data": "response"}
    )
    mock_request.callback = mocker.Mock(return_value={"parsed": "data"})

    result = await data_service._fetch(requests_iterable)
    assert result == [{"parsed": "data"}, {"parsed": "data"}]
    assert data_service.client.make_request.call_count == 2
    assert mock_request.callback.call_count == 2


single_request = [Request(url="http://example.com", callback=lambda x: x)]


async def mock_async_generator():
    for i in range(2):
        yield Request(url="http://example.com", callback=lambda x: x)


def mock_sync_generator():
    for i in range(2):
        yield Request(url="http://example.com", callback=lambda x: x)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "requests_iterable, expected",
    [(single_request, 1), (mock_async_generator(), 2), (mock_sync_generator(), 2)],
)
async def test_process_item(data_service, requests_iterable, expected):
    # Test with a single request
    result = [task async for task in data_service._process_item(requests_iterable)]
    assert len(result) == expected
