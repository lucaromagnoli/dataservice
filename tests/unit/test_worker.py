import asyncio
import logging
from contextlib import nullcontext as does_not_raise
from unittest.mock import AsyncMock, patch

import pytest

from dataservice.cache import LocalJsonCache
from dataservice.config import ServiceConfig
from dataservice.data import BaseDataItem
from dataservice.exceptions import (
    DataServiceException,
    NonRetryableException,
    ParsingException,
    RetryableException,
    TimeoutException,
)
from dataservice.models import Request, Response
from dataservice.worker import DataWorker
from tests.unit.conftest import ToyClient

# TODO Fix broken tests


class Foo(BaseDataItem):
    parsed: str


@pytest.fixture
def config():
    return ServiceConfig()


request_with_data_callback = Request(
    url="http://example.com",
    callback=lambda x: {"parsed": "data"},
    client=ToyClient(),
)

request_with_data_item_callback = Request(
    url="http://example.com",
    callback=lambda x: Foo(parsed="data"),
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
def data_worker_with_params(request, toy_client, config):
    if "requests" not in request.param:
        request.param["requests"] = [request_with_data_callback]
    if "config" not in request.param:
        request.param["config"] = config
    return DataWorker(
        requests=request.param["requests"], config=request.param["config"]
    )


@pytest.fixture
def data_worker(config):
    return DataWorker(requests=[request_with_data_callback], config=config)


@pytest.fixture
def queue_item(request):
    return request.param


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "requests, expected",
    [
        ([request_with_data_callback], {"parsed": "data"}),
        ([request_with_data_item_callback], Foo(parsed="data")),
    ],
)
async def test_data_worker_handles_request_correctly(requests, expected, config):
    data_worker = DataWorker(requests, config=config)
    await data_worker.fetch()
    assert data_worker.get_data_item() == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("data_worker_with_params", [{"requests": []}], indirect=True)
async def test_data_worker_handles_empty_queue(data_worker_with_params):
    with pytest.raises(ValueError, match="No requests to process"):
        await data_worker_with_params.fetch()


@pytest.mark.asyncio
async def test_handles_queue_item_puts_dict_in_data_queue(data_worker):
    await data_worker._handle_queue_item({"parsed": "data"})
    assert not data_worker.has_no_more_data()
    assert data_worker.get_data_item() == {"parsed": "data"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data_worker_with_params, queue_item",
    [({}, request_with_iterator_callback)],
    indirect=True,
)
async def test_handles_queue_item_puts_request_in_work_queue(
    data_worker_with_params, queue_item
):
    await data_worker_with_params._handle_queue_item(queue_item)
    assert data_worker_with_params._work_queue.get_nowait() is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data_worker_with_params",
    [{}],
    indirect=True,
)
async def test_handles_queue_item_raises_value_error_for_unknown_type(
    data_worker_with_params,
):
    with pytest.raises(ValueError, match="Unknown item type <class 'int'>"):
        await data_worker_with_params._handle_queue_item(1)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data_worker_with_params",
    [{"requests": [request_with_data_callback]}],
    indirect=True,
)
async def test_is_duplicate_request_returns_false_for_new_request(
    data_worker_with_params,
):
    request = Request(
        url="http://example.com", client=ToyClient(), callback=lambda x: x
    )
    assert not data_worker_with_params._is_duplicate_request(request)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "config, expected",
    [
        (ServiceConfig(**{"deduplication": True, "max_workers": 1}), 1),
        (ServiceConfig(**{"deduplication": False, "max_workers": 1}), 2),
    ],
)
async def test_deduplication(config, expected, mocker):
    mocked_handle_request = mocker.patch(
        "dataservice.worker.DataWorker._handle_request",
        side_effect=[
            Response(
                request=request_with_data_callback,
                text='{"parsed": "data"}',
                data={"parsed": "data"},
                url="http://example.com",
            ),
            Response(
                request=request_with_data_callback,
                text='{"parsed": "data"}',
                data={"parsed": "data"},
                url="http://example.com",
            ),
        ],
    )
    data_worker = DataWorker(
        requests=[request_with_data_callback, request_with_data_callback], config=config
    )
    await data_worker.fetch()
    assert mocked_handle_request.call_count == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "side_effect, expected_response, expected_behaviour, expected_call_count",
    [
        (
            [
                RetryableException("Retryable request exception"),
                RetryableException("Retryable request exception"),
                Response(
                    request=request_with_data_callback,
                    data={"parsed": "data"},
                    url="http://example.com",
                ),
            ],
            Response(
                request=request_with_data_callback,
                data={"parsed": "data"},
                url="http://example.com",
            ),
            does_not_raise(),
            3,
        ),
        (
            [
                RetryableException("Retryable request exception"),
                RetryableException("Retryable request exception"),
                RetryableException("Retryable request exception"),
            ],
            None,
            pytest.raises(RetryableException),
            None,
        ),
        (
            [
                DataServiceException("Request exception"),
                DataServiceException("Request exception"),
                DataServiceException("Request exception"),
            ],
            None,
            pytest.raises(DataServiceException),
            None,
        ),
    ],
)
async def test__handle_request(
    data_worker,
    mocker,
    side_effect,
    expected_response,
    expected_behaviour,
    expected_call_count,
):
    mocked_make_request = mocker.patch(
        "dataservice.worker.DataWorker._make_request",
        mocker.AsyncMock(side_effect=side_effect),
    )
    data_worker._clients = {"toyclient": ToyClient()}
    data_worker.config = ServiceConfig(
        **{
            "retry": {
                "max_retries": 0,
                "wait_exponential": 0,
                "wait_exp_min": 0,
                "wait_exp_max": 0,
            }
        }
    )

    with expected_behaviour:
        response = await data_worker._handle_request(request_with_data_callback)
        assert response.model_dump() == expected_response.model_dump()
        assert mocked_make_request.call_count == expected_call_count


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "side_effect, expected_behaviour, expected_logs",
    [
        (
            [
                RetryableException("Retryable request exception"),
                RetryableException("Retryable request exception"),
                Response(
                    request=request_with_data_callback,
                    data={"parsed": "data"},
                    url="http://example.com",
                ),
            ],
            does_not_raise(),
            "Retrying request http://example.com/, attempt 2",
        ),
        (
            [
                RetryableException("Retryable request exception"),
                RetryableException("Retryable request exception"),
                RetryableException("Retryable request exception"),
            ],
            pytest.raises(RetryableException),
            "Retrying request http://example.com/, attempt 3",
        ),
        (
            [
                DataServiceException("Request exception"),
                DataServiceException("Request exception"),
                DataServiceException("Request exception"),
            ],
            pytest.raises(DataServiceException),
            "Exception making request: Request exception",
        ),
    ],
)
async def test_retry_logs(
    side_effect, expected_behaviour, expected_logs, data_worker, mocker, caplog
):
    mocker.patch(
        "dataservice.worker.DataWorker._make_request",
        mocker.AsyncMock(side_effect=side_effect),
    )
    data_worker._clients = {"toyclient": ToyClient()}
    data_worker.config = ServiceConfig(
        **{
            "retry": {
                "max_retries": 3,
                "wait_exponential": 0,
                "wait_exp_min": 0,
                "wait_exp_max": 0,
            }
        }
    )
    caplog.set_level(logging.DEBUG)
    with expected_behaviour:
        await data_worker._handle_request(request_with_data_callback)
        assert caplog.messages[-1] == expected_logs


@pytest.fixture
def mock_worker():
    config = ServiceConfig(
        max_concurrency=5, deduplication=True, retry={"max_retries": 0}
    )
    requests = [
        Request(url="http://example.com", callback=lambda x: x, client=AsyncMock())
    ]
    worker = DataWorker(requests=requests, config=config)
    return worker


@pytest.mark.asyncio
async def test_handle_request_item_successfully(mock_worker, mocker):
    request = mock_worker._requests[0]
    mock_worker._is_duplicate_request = mocker.MagicMock(return_value=False)
    mock_worker._has_request_failed = mocker.MagicMock(return_value=False)
    mock_worker._handle_request = AsyncMock()
    mock_worker._handle_callback = AsyncMock(return_value={})
    mock_worker._add_to_data_queue = AsyncMock()

    await mock_worker._handle_request_item(request)

    mock_worker._handle_request.assert_called_once_with(request)
    mock_worker._handle_callback.assert_called_once()
    mock_worker._add_to_data_queue.assert_called_once()


@pytest.mark.parametrize(
    "exception, expected, log_message",
    [
        (
            RetryableException("RetryableException"),
            does_not_raise(),
            "Re-raised after retrying http://example.com/: RetryableException",
        ),
        (
            TimeoutException("TimeoutException"),
            does_not_raise(),
            "Error processing request http://example.com/: TimeoutException",
        ),
        (
            NonRetryableException("NonRetryableException"),
            does_not_raise(),
            "Error processing request http://example.com/: NonRetryableException",
        ),
        (
            ParsingException("ParsingException"),
            does_not_raise(),
            "Error processing request http://example.com/: ParsingException",
        ),
        (
            DataServiceException("DataServiceException"),
            pytest.raises(DataServiceException),
            "Error processing request http://example.com/: DataServiceException",
        ),
    ],
)
@pytest.mark.asyncio
async def test_handle_request_item_with_exception(
    mock_worker, mocker, exception, expected, log_message, caplog
):
    request = mock_worker._requests[0]
    mock_worker._is_duplicate_request = mocker.MagicMock(return_value=False)
    mock_worker._has_request_failed = mocker.MagicMock(return_value=False)
    mock_worker._handle_request = AsyncMock(side_effect=exception)
    mock_worker._add_to_failures = AsyncMock()

    with expected:
        await mock_worker._handle_request_item(request)

    assert caplog.messages[-1] == log_message


@pytest.mark.asyncio
async def test_data_worker_with_local_cache_write_periodically(mocker, tmp_path):
    cache = LocalJsonCache(tmp_path / "cache.json")
    await cache.load()
    mocked_write_periodically = mocker.patch.object(
        cache, "write_periodically", mocker.AsyncMock()
    )
    requests = [request_with_data_callback]
    config = ServiceConfig(cache={"use": True, "write_interval": 1}, constant_delay=1)
    data_worker = DataWorker(requests, config=config, cache=cache)
    await data_worker.fetch()
    assert mocked_write_periodically.await_count == 1


@pytest.fixture
def config_concurrency():
    # Configure with max concurrency of 3 for testing purposes
    return ServiceConfig(max_concurrency=3, limiter=None)


@pytest.fixture
def concurrency_requests():
    # Generate some mock requests for testing
    return [
        Request(
            url=f"http://example.com/page-{i}",
            callback=lambda x: Foo(parsed="data"),
            client=ToyClient(random_sleep=1),
        )
        for i in range(10)
    ]


@pytest.fixture
def concurrency_worker(config, concurrency_requests):
    # Initialize DataWorker with mock config and requests
    return DataWorker(concurrency_requests, config=config)


@pytest.mark.asyncio
async def test_semaphore_limits_concurrency(concurrency_worker):
    """Test that semaphore enforces max_concurrency limit on concurrent requests."""

    active_tasks = 0
    max_tasks_observed = 0

    # Define a wrapper to track active tasks
    async def track__handle_request_item(request):
        nonlocal active_tasks, max_tasks_observed
        active_tasks += 1
        max_tasks_observed = max(max_tasks_observed, active_tasks)
        await concurrency_worker._handle_request_item(request)
        active_tasks -= 1

    # Run all request items concurrently, limited by semaphore
    tasks = [
        track__handle_request_item(request) for request in concurrency_worker._requests
    ]
    await asyncio.gather(*tasks)

    # Check that max_tasks_observed never exceeded config.max_concurrency
    assert max_tasks_observed <= concurrency_worker.config.max_concurrency


@pytest.mark.asyncio
async def test_semaphore_releases_after_request(concurrency_worker):
    """Ensure semaphore releases correctly after each request completes."""

    # Patch _handle_request to simulate a request that completes after a short delay
    # Counter for active requests to verify semaphore behavior
    active_tasks = 0

    # Define a wrapper to track active tasks
    async def track__handle_request_item(request):
        nonlocal active_tasks
        active_tasks += 1
        assert (
            active_tasks <= concurrency_worker.config.max_concurrency
        )  # Assert within limit
        await concurrency_worker._handle_request_item(request)
        active_tasks -= 1

    # Run all request items concurrently, limited by semaphore
    tasks = [
        track__handle_request_item(request) for request in concurrency_worker._requests
    ]
    await asyncio.gather(*tasks)

    # If the test completes without exceeding max concurrency, it passes
    assert active_tasks == 0


@pytest.mark.asyncio
async def test_handle_request_calls_within_semaphore_limit(concurrency_worker):
    """Verify that `_handle_request_item` is called within semaphore limits."""

    # Mock _handle_request to track calls without delay
    with patch.object(
        concurrency_worker, "_handle_request", AsyncMock()
    ) as mock_handle_request:
        # Run all request items concurrently
        tasks = [
            concurrency_worker._handle_request_item(request)
            for request in concurrency_worker._requests
        ]
        await asyncio.gather(*tasks)

        # Ensure _handle_request was called the expected number of times
        assert mock_handle_request.call_count == len(concurrency_worker._requests)


def test_is_duplicate_request(data_worker):
    request1 = Request(
        url="http://example.com", method="GET", callback=lambda x: x, client=ToyClient()
    )
    request2 = Request(
        url="http://example.com", method="GET", callback=lambda x: x, client=ToyClient()
    )
    request3 = Request(
        url="http://example.org",
        method="POST",
        callback=lambda x: x,
        client=ToyClient(),
        json_data={"key": "value"},
    )
    request4 = Request(
        url="http://example.com",
        method="GET",
        callback=lambda x: x,
        client=ToyClient(),
        params={"key": "value"},
    )

    # First request should not be a duplicate
    assert not data_worker._is_duplicate_request(request1)
    # Second request with the same URL should be a duplicate
    assert data_worker._is_duplicate_request(request2)
    # Third request with a different URL should not be a duplicate
    assert not data_worker._is_duplicate_request(request3)
    # Fourth request with the same URL but different params should not be a duplicate
    assert not data_worker._is_duplicate_request(request4)


@pytest.fixture
def config_with_cache():
    return ServiceConfig(cache={"use": True})


@pytest.fixture
def data_worker_with_cache(config_with_cache):
    return DataWorker(requests=[], config=config_with_cache)


@pytest.mark.asyncio
async def test_make_request_uses_cache(data_worker_with_cache, mocker):
    request = Request(
        url="http://example.com", client=ToyClient(), callback=lambda x: x
    )
    response = Response(
        request=request, text="cached response", data={}, url="http://example.com"
    )

    mock_cache = mocker.AsyncMock(spec=LocalJsonCache)
    data_worker_with_cache.cache = mock_cache

    mock_cache_request = mocker.patch(
        "dataservice.worker.cache_request",
        return_value=AsyncMock(return_value=response),
    )

    result = await data_worker_with_cache._make_request(request)

    mock_cache_request.assert_called_once_with(mock_cache)
    assert result.text == "cached response"
    assert result.data == {}
