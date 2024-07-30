import pytest
from contextlib import nullcontext as does_not_raise
from dataservice.models import Request


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "item, queue_put_call_count, response, context",
    [
        pytest.param(
            Request(url="http://example.com", callback=lambda x: {"parsed": "data"}),
            0,
            {"parsed": "data"},
            does_not_raise(),
            id="Single request. Returns parsed data but no items in queue",
        ),
        pytest.param(
            Request(
                url="http://example.com",
                callback=lambda x: (
                    Request(
                        url=f"http://example.com/item{i}",
                        callback=lambda y: {"data_item": f"item{i}"},
                    )
                    for i in range(10)
                ),
            ),
            1,
            None,
            does_not_raise(),
            id="Generator request. Does not return but put items in queue",
        ),
    ],
)
async def test_handle_queue_item(
    data_service_mock_queue, item, queue_put_call_count, response, context
):
    with context:
        assert await data_service_mock_queue._handle_queue_item(item) == response
        assert data_service_mock_queue.client.make_request.call_count == 1
        assert data_service_mock_queue._queue.put.call_count == queue_put_call_count


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "items_in_queue, max_items, expected",
    [
        pytest.param(10, 10, 10, id="Max items is equal to items in queue"),
        pytest.param(10, 5, 5, id="Max items is less than items in queue"),
        pytest.param(2, 5, 2, id="Max items is greater than items in queue"),
        pytest.param(0, 5, 0, id="No items in queue"),
    ],
)
async def test_get_batch_items_from_queue(
    data_service, mock_request, items_in_queue, max_items, expected
):
    for _ in range(items_in_queue):
        await data_service._queue.put(mock_request)

    items = await data_service._get_batch_items_from_queue(max_items)
    assert len(items) == expected


@pytest.mark.asyncio
async def test_fetch(data_service, mock_request, mocker):
    requests_iterable = [mock_request, mock_request]
    data_service.start_requests = requests_iterable
    data_service.client.make_request = mocker.AsyncMock(
        return_value={"data": "response"}
    )
    mock_request.callback = mocker.Mock(return_value={"parsed": "data"})

    result = [i async for i in data_service.fetch()]
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
