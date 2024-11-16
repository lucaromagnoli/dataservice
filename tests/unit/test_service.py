from __future__ import annotations

import asyncio
import signal
import uuid
from contextlib import nullcontext as does_not_raise

import pytest

from dataservice.data import BaseDataItem
from dataservice.models import Request, Response
from dataservice.service import AsyncDataService, DataService
from tests.unit.conftest import ToyClient


class Foo(BaseDataItem):
    """Mock data item class"""

    foo: str


@pytest.fixture
def toy_client():
    return ToyClient(random_sleep=0)


@pytest.fixture
def start_requests():
    urls = [
        "https://www.foobar.com",
        "https://www.barbaz.com",
    ]
    return [Request(url=url, callback=parse_items, client=ToyClient()) for url in urls]


@pytest.fixture
def file_path(tmp_path):
    return tmp_path / "test.json"


@pytest.fixture
def data_service(toy_client, start_requests):
    return DataService(requests=start_requests)


@pytest.fixture
def async_data_service(toy_client, start_requests):
    return AsyncDataService(requests=start_requests)


async def parse_items(response: Response):
    """Mock function that parses a list of items from a response and makes a request for each item"""
    for i in range(1, 21):
        soup = response.html
        soup.find("home")
        url = f"{response.request.url}item_{i}"
        yield Request(url=url, callback=parse_item, client=ToyClient())


def parse_item(response: Response):
    """Mock function that returns a data item from the response"""
    return {"url": response.request.url, "item_id": uuid.uuid4()}


def test_toy_service(data_service):
    data = tuple(data_service)
    assert len(data) == 40
    assert set([d["url"] for d in data[:20]]) == set(
        [f"https://www.foobar.com/item_{i}" for i in range(1, 21)]
    )
    assert set([d["url"] for d in data[20:]]) == set(
        [f"https://www.barbaz.com/item_{i}" for i in range(1, 21)]
    )


@pytest.mark.asyncio
async def test_toy_async_service(async_data_service):
    data = [datum async for datum in async_data_service]
    assert len(data) == 40
    assert set([d["url"] for d in data[:20]]) == set(
        [f"https://www.foobar.com/item_{i}" for i in range(1, 21)]
    )
    assert set([d["url"] for d in data[20:]]) == set(
        [f"https://www.barbaz.com/item_{i}" for i in range(1, 21)]
    )


@pytest.mark.parametrize(
    "results, expected_behaviour",
    [
        ([{"a": "a"}], does_not_raise()),
        ([Foo(foo="bar")], does_not_raise()),
    ],
)
def test_write_args_validation(file_path, results, expected_behaviour, data_service):
    with expected_behaviour:
        data_service.write(file_path, results)


@pytest.mark.asyncio
async def test_run_data_worker(mocker):
    service = AsyncDataService([])
    mocker.patch.object(service, "_data_worker", new_callable=mocker.AsyncMock)
    mocker.patch.object(service, "register_signal_handlers")
    mocker.patch.object(service, "cleanup_signal_handlers")

    service.data_worker.fetch = mocker.AsyncMock()
    service.data_worker.has_started = False

    await service._run_data_worker()

    service.register_signal_handlers.assert_called_once()
    service.data_worker.fetch.assert_awaited_once()
    service.cleanup_signal_handlers.assert_called_once()


@pytest.mark.asyncio
async def test_registers_signal_handlers_correctly(mocker):
    mocker.patch("asyncio.get_running_loop", return_value=mocker.Mock())
    service = AsyncDataService([])
    service.register_signal_handlers()
    loop = asyncio.get_running_loop()
    loop.add_signal_handler.assert_any_call(signal.SIGINT, service._handle_stop_signal)
    loop.add_signal_handler.assert_any_call(signal.SIGTERM, service._handle_stop_signal)


@pytest.mark.asyncio
async def test_cleans_up_signal_handlers_correctly(mocker):
    mocker.patch("asyncio.get_running_loop", return_value=mocker.Mock())
    service = AsyncDataService([])
    service.cleanup_signal_handlers()
    loop = asyncio.get_running_loop()
    loop.remove_signal_handler.assert_any_call(signal.SIGINT)
    loop.remove_signal_handler.assert_any_call(signal.SIGTERM)
