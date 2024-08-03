import pytest

from dataservice.models import Request
from worker import DataWorker
from tests.unit.clients import ToyClient


@pytest.fixture
def config():
    return {"max_workers": 1, "deduplication": False, "deduplication_keys": ["url"]}


request_with_data_callback = Request(
    url="http://example.com",
    callback=lambda x: {"parsed": "data"},
    client=ToyClient(),
)

request_with_iterator_callback = Request(
    url="http://example.com",
    callback=lambda x: iter(
        Request(
            url="http://example.com",
            client=ToyClient(),
            callback=lambda x: {"parsed": "data"},
        )
    ),
    client=ToyClient(),
)


@pytest.fixture
def data_worker(request, toy_client, config):
    if "requests" not in request.param:
        request.param["requests"] = [
            Request(
                url="http://example.com",
                callback=lambda x: {"parsed": "data"},
                client=ToyClient(),
            )
        ]

    request.param["config"] = {**config, **(request.param.get("config") or {})}
    return DataWorker(
        requests=request.param["requests"], config=request.param["config"]
    )


@pytest.fixture
def queue_item(request):
    return request.param


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data_worker",
    [{}],
    indirect=True,
)
async def test_data_worker_handles_request_correctly(data_worker):
    await data_worker.fetch()
    assert data_worker.get_data_item() == {"parsed": "data"}


@pytest.mark.asyncio
@pytest.mark.parametrize("data_worker", [{"requests": []}], indirect=True)
async def test_data_worker_handles_empty_queue(data_worker):
    with pytest.raises(ValueError, match="No requests to process"):
        await data_worker.fetch()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data_worker, queue_item",
    [
        (
            {},
            request_with_data_callback,
        )
    ],
    indirect=True,
)
async def test_handles_request_item_puts_dict_in_data_queue(data_worker, queue_item):
    await data_worker._handle_queue_item(queue_item)
    assert not data_worker.has_no_more_data()
    assert data_worker.get_data_item() == {"parsed": "data"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data_worker, queue_item", [({}, request_with_iterator_callback)], indirect=True
)
async def test_handles_request_item_puts_request_in_work_queue(data_worker, queue_item):
    await data_worker._handle_queue_item(queue_item)
    assert data_worker._work_queue.get_nowait() is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data_worker",
    [{}],
    indirect=True,
)
async def test_handles_queue_item_raises_value_error_for_unknown_type(
    data_worker, mocker
):
    with pytest.raises(ValueError, match="Unknown item type <class 'int'>"):
        await data_worker._handle_queue_item(1)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data_worker", [{"requests": [request_with_data_callback]}], indirect=True
)
async def test_is_duplicate_request_returns_false_for_new_request(data_worker):
    request = Request(
        url="http://example.com", client=ToyClient(), callback=lambda x: x
    )
    assert not data_worker._is_duplicate_request(request)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "config, expected",
    [
        ({"deduplication": True, "max_workers": 1, "deduplication_keys": ["url"]}, 1),
        ({"deduplication": False, "max_workers": 1, "deduplication_keys": ["url"]}, 2),
    ],
)
async def test_deduplication(config, expected, mocker):
    mocked_handle_request = mocker.patch(
        "worker.DataWorker._handle_request", return_value=[{"parsed": "data"}]
    )
    data_worker = DataWorker(
        requests=[request_with_data_callback, request_with_data_callback], config=config
    )
    await data_worker.fetch()
    assert mocked_handle_request.call_count == expected
