from __future__ import annotations

import signal
import uuid
from contextlib import nullcontext as does_not_raise

import anyio
import pytest

from dataservice.data import BaseDataItem
from dataservice.models import Request, Response
from dataservice.service import AsyncDataService, DataService
from dataservice.worker import DataWorker
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


@pytest.mark.anyio
async def test_handles_stop_signals_correctly(mocker):
    # Mock the signal receiver to yield a signal
    async def mock_signals():
        yield signal.SIGINT

    mock_signal_receiver = mocker.MagicMock()
    mock_signal_receiver.__enter__.return_value = mock_signals()
    mock_signal_receiver.__exit__ = mocker.MagicMock()

    # Patch `anyio.open_signal_receiver`
    mocker.patch("anyio.open_signal_receiver", return_value=mock_signal_receiver)

    # Initialize the service
    service = AsyncDataService([])
    mocker.patch.object(service, "handle_stop_signal", mocker.AsyncMock())

    # Run the signal handling method
    await service.handle_signals()

    # Assert that the stop signal handler was called
    service.handle_stop_signal.assert_called_once()


@pytest.mark.anyio
async def test_does_not_handle_unrelated_signals(mocker):
    # Mock the signal receiver to yield a signal
    async def mock_signals():
        yield signal.SIGUSR1

    mock_signal_receiver = mocker.MagicMock()
    mock_signal_receiver.__enter__.return_value = mock_signals()
    mock_signal_receiver.__exit__ = mocker.MagicMock()

    # Patch `anyio.open_signal_receiver`
    mocker.patch("anyio.open_signal_receiver", return_value=mock_signal_receiver)

    # Initialize the service
    service = AsyncDataService([])
    mocker.patch.object(service, "handle_stop_signal", mocker.AsyncMock())

    # Run the signal handling method
    await service.handle_signals()

    # Assert that the stop signal handler was called
    service.handle_stop_signal.assert_not_called()


@pytest.mark.anyio
async def test_service_handles_stop_signal(mocker):
    """Test that the service gracefully stops when a signal is sent."""

    # Mock request and callback
    mock_request = Request(
        url="https://example.com", callback=mocker.AsyncMock(), client=ToyClient()
    )
    mock_requests = [mock_request]

    # Mock configuration
    mock_config = mocker.Mock()
    mock_config.cache = mocker.Mock()
    mock_config.cache.use = False
    mock_config.max_concurrency = 1
    mock_config.limiter = None

    # Mock DataWorker
    class MockDataWorker(DataWorker):
        async def fetch(self, stop_event: anyio.Event) -> None:
            # Simulate processing
            for _ in range(5):
                if stop_event.is_set():
                    break
                await anyio.sleep(0.1)  # Simulated work

    # Replace DataWorker with MockDataWorker
    AsyncDataService.data_worker = property(
        lambda self: MockDataWorker(mock_requests, config=mock_config)
    )

    # Initialize the service
    service = AsyncDataService(mock_requests, config=mock_config)

    async def mock_signals():
        yield signal.SIGINT

    mock_signal_receiver = mocker.MagicMock()
    mock_signal_receiver.__enter__.return_value = mock_signals()
    mock_signal_receiver.__exit__ = mocker.MagicMock()

    # Patch `anyio.open_signal_receiver`
    mocker.patch("anyio.open_signal_receiver", return_value=mock_signal_receiver)

    # Run the service and verify behavior
    async with anyio.create_task_group() as tg:
        tg.start_soon(service.handle_signals)  # Start signal handling
        tg.start_soon(service._run_data_worker)  # Start the worker

    # Ensure the stop event was set
    assert service._stop_event.is_set()

    # Verify that the worker stopped gracefully
    mock_request.callback.assert_not_called()  # Mock callback shouldn't be processed fully
