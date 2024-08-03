import pytest

from dataservice.models import Request
from dataservice.service import DataWorker

request_with_data_callback = Request(
    url="http://example.com",
    callback=lambda x: {"parsed": "data"},
    client="ToyClient",
)

request_with_iterator_callback = Request(
    url="http://example.com",
    callback=lambda x: iter(Request(url="http://example.com", client="ToyClient", callback=lambda x: {"parsed": "data"})),
    client="ToyClient",
)


@pytest.fixture
def data_worker(request, toy_client):
    if "requests" not in request.param:
        request.param["requests"] = [
            Request(
                url="http://example.com",
                callback=lambda x: {"parsed": "data"},
                client="ToyClient",
            )
        ]
    if "clients" not in request.param:
        request.param["clients"] = (toy_client,)
    return DataWorker(
        requests=request.param["requests"], clients=request.param["clients"]
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
@pytest.mark.parametrize("data_worker, queue_item", [({}, request_with_iterator_callback)], indirect=True)
async def test_handles_request_item_puts_request_in_work_queue(data_worker, queue_item):
    await data_worker._handle_queue_item(queue_item)
    assert data_worker.get_work_item() is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data_worker",
    [{}],
    indirect=True,
)
async def test_handles_queue_item_raises_value_error_for_unknown_type(data_worker, mocker):
    with pytest.raises(ValueError, match="Unknown item type <class 'int'>"):
        await data_worker._handle_queue_item(1)

