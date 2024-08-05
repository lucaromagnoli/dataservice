import logging
import os
from contextlib import nullcontext as does_not_raise
from dataclasses import dataclass

import pytest

from dataservice.config import ServiceConfig
from dataservice.exceptions import RequestException, RetryableRequestException
from dataservice.models import Request, Response
from dataservice.worker import DataWorker
from tests.unit.conftest import ToyClient


@dataclass
class Foo:
    parsed: str


@pytest.fixture
def config():
    return ServiceConfig()


request_with_data_callback = Request(
    url="http://example.com",
    callback=lambda x: {"parsed": "data"},
    client=ToyClient(),
)

request_with_dataclass_callback = Request(
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
def os_environ():
    os.environ["MAX_RETRIES"] = "0"
    os.environ["WAIT_EXP_MUL"] = "0"
    os.environ["WAIT_EXP_MIN"] = "0"
    os.environ["WAIT_EXP_MAX"] = "0"
    yield
    del os.environ["MAX_RETRIES"]
    del os.environ["WAIT_EXP_MUL"]
    del os.environ["WAIT_EXP_MIN"]
    del os.environ["WAIT_EXP_MAX"]


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
        ([request_with_dataclass_callback], Foo(parsed="data")),
    ],
)
async def test_data_worker_handles_request_correctly(requests, expected, config):
    data_worker = DataWorker(requests, config)
    await data_worker.fetch()
    assert data_worker.get_data_item() == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("data_worker_with_params", [{"requests": []}], indirect=True)
async def test_data_worker_handles_empty_queue(data_worker_with_params):
    with pytest.raises(ValueError, match="No requests to process"):
        await data_worker_with_params.fetch()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data_worker_with_params, queue_item",
    [
        (
            {},
            request_with_data_callback,
        )
    ],
    indirect=True,
)
async def test_handles_queue_item_puts_dict_in_data_queue(
    data_worker_with_params, queue_item
):
    await data_worker_with_params._handle_queue_item(queue_item)
    assert not data_worker_with_params.has_no_more_data()
    assert data_worker_with_params.get_data_item() == {"parsed": "data"}


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
    data_worker_with_params, mocker
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
            Response(request=request_with_data_callback, data={"parsed": "data"}),
            Response(request=request_with_data_callback, data={"parsed": "data"}),
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
                RetryableRequestException("Retryable request exception"),
                RetryableRequestException("Retryable request exception"),
                Response(request=request_with_data_callback, data={"parsed": "data"}),
            ],
            Response(request=request_with_data_callback, data={"parsed": "data"}),
            does_not_raise(),
            3,
        ),
        (
            [
                RetryableRequestException("Retryable request exception"),
                RetryableRequestException("Retryable request exception"),
                RetryableRequestException("Retryable request exception"),
            ],
            None,
            pytest.raises(RetryableRequestException),
            None,
        ),
        (
            [
                RequestException("Request exception"),
                RequestException("Request exception"),
                RequestException("Request exception"),
            ],
            None,
            pytest.raises(RequestException),
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
                RetryableRequestException("Retryable request exception"),
                RetryableRequestException("Retryable request exception"),
                Response(request=request_with_data_callback, data={"parsed": "data"}),
            ],
            does_not_raise(),
            "Retrying request http://example.com/, attempt 3",
        ),
        (
            [
                RetryableRequestException("Retryable request exception"),
                RetryableRequestException("Retryable request exception"),
                RetryableRequestException("Retryable request exception"),
            ],
            pytest.raises(RetryableRequestException),
            "Retrying request http://example.com/, attempt 3",
        ),
        (
            [
                RequestException("Request exception"),
                RequestException("Request exception"),
                RequestException("Request exception"),
            ],
            pytest.raises(RequestException),
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
                "max_retries": 2,
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
