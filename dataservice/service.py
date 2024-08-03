"""
DataService: Manages the overall data processing service, including initialization, iteration, and running the data worker.
DataWorker: Handles the actual data processing tasks, including managing queues, handling requests, and processing data items.
"""
from __future__ import annotations
import asyncio
import os
from logging import getLogger
from typing import Any, AsyncGenerator, Generator, Optional

from dataservice.models import Request, RequestsIterable, Response

MAX_ASYNC_TASKS = int(os.environ.get("MAX_ASYNC_TASKS", "10"))
logger = getLogger(__name__)

__all__ = ["DataService"]


class DataService:
    """
    A service class to handle data requests and processing.
    """

    def __init__(
        self, requests: RequestsIterable, config: Optional[dict[str, Any]] = None
    ):
        """
        Initializes the DataService with the given parameters.
        """
        default_config = {
            "max_async_tasks": MAX_ASYNC_TASKS,
            "deduplication": True,
            "deduplication_keys": ("url",),
        }
        self._requests = requests
        self._config = {**default_config, **(config or {})}
        self._data_worker: Optional[DataWorker] = None

    @property
    def config(self) -> dict[str, Any]:
        """
        Returns the configuration dictionary.
        """
        return self._config

    @property
    def data_worker(self) -> DataWorker:
        """
        Lazy initialization of the DataWorker instance.
        """
        if self._data_worker is None:
            self._data_worker = DataWorker(self._requests, self.config)
        return self._data_worker

    def __iter__(self) -> DataService:
        """
        Returns the iterator object itself.
        """
        return self

    def __next__(self) -> Any:
        """
        Fetches the next data item from the data worker.
        """
        self._run_data_worker()
        if self.data_worker.has_no_more_data():
            raise StopIteration
        return self.data_worker.get_data_item()

    def _run_data_worker(self) -> None:
        """
        Runs the data worker to fetch data items.
        """
        asyncio.run(self.data_worker.fetch())


class DataWorker:
    """
    A worker class to handle asynchronous data processing.
    """

    def __init__(self, requests: RequestsIterable, config: dict[str, Any]):
        """
        Initializes the DataWorker with the given parameters.
        """
        self.max_async_tasks: int = config["max_async_tasks"]
        self._deduplication: bool = config["deduplication"]
        self._deduplication_keys: tuple = config["deduplication_keys"]
        self._requests: RequestsIterable = requests
        self._work_queue: asyncio.Queue = asyncio.Queue()
        self._data_queue: asyncio.Queue = asyncio.Queue()
        self._seen_requests: set = set()
        self._started: bool = False
        self._clients: dict[Any, Any] = {}

    async def _get_batch_items_from_queue(self) -> list:
        """
        Retrieves a batch of items from the work queue.
        """
        items = []
        while not self._work_queue.empty() and len(items) < self.max_async_tasks:
            items.append(await self._work_queue.get())
        return items

    async def _add_to_work_queue(self, item: Any) -> None:
        """
        Adds an item to the work queue.
        """
        await self._work_queue.put(item)

    async def _add_to_data_queue(self, item: Any) -> None:
        """
        Adds an item to the data queue.
        """
        await self._data_queue.put(item)

    async def _enqueue_start_requests(self) -> None:
        """
        Enqueues the initial set of requests to the work queue.
        """
        if isinstance(self._requests, AsyncGenerator):
            async for request in self._requests:
                await self._add_to_work_queue(request)
        else:
            for request in self._requests:
                await self._add_to_work_queue(request)
        if self._work_queue.empty():
            raise ValueError("No requests to process.")
        self._started = True

    async def _handle_queue_item(self, item: Any) -> None:
        """
        Handles an item from the work queue.
        """
        if isinstance(item, Request):
            await self._handle_request_item(item)
        elif isinstance(item, dict):
            await self._add_to_data_queue(item)
        else:
            raise ValueError(f"Unknown item type {type(item)}")

    def _is_duplicate_request(self, request: Request) -> bool:
        """
        Checks if a request is a duplicate.
        """
        key = request.url
        if key in self._seen_requests:
            return True
        self._seen_requests.add(key)
        return False

    async def _handle_request_item(self, request: Request) -> None:
        """
        Handles a request item.
        """
        if self._deduplication and self._is_duplicate_request(request):
            return
        response = await self._handle_request(request)
        callback_result = request.callback(response)
        if isinstance(callback_result, dict):
            await self._add_to_data_queue(callback_result)
        else:
            await self._add_to_work_queue(callback_result)

    async def _handle_request(self, request: Request) -> Response:
        """
        Makes an asynchronous request.
        """
        if request.client not in self._clients:
            self._clients[request.client] = request.client()

        client = self._clients[request.client]
        return await client.make_request(request)

    async def _iter_callbacks(self, item: Any) -> AsyncGenerator:
        """
        Iterates over callbacks and creates tasks for them.
        """
        if isinstance(item, Generator):
            for i in item:
                yield asyncio.create_task(self._handle_queue_item(i))
        elif isinstance(item, AsyncGenerator):
            async for i in item:
                yield asyncio.create_task(self._handle_queue_item(i))
        elif isinstance(item, (Request, dict)):
            yield asyncio.create_task(self._handle_queue_item(item))
        else:
            raise ValueError(f"Unknown item type {type(item)}")

    async def fetch(self) -> None:
        """
        Fetches data items by processing the work queue.
        """
        if not self._started:
            await self._enqueue_start_requests()
        while self.has_jobs():
            logger.debug(f"Work queue size: {self._work_queue.qsize()}")
            async with asyncio.Semaphore(self.max_async_tasks):
                items = await self._get_batch_items_from_queue()
                tasks = [
                    task for item in items async for task in self._iter_callbacks(item)
                ]
                await asyncio.gather(*tasks)

    def get_data_item(self) -> Any:
        """
        Retrieves a data item from the data queue.
        """
        return self._data_queue.get_nowait()

    def has_no_more_data(self) -> bool:
        """
        Checks if there are no more data items in the data queue.
        """
        return self._data_queue.empty()

    def has_jobs(self) -> bool:
        """
        Checks if there are jobs in the work queue.
        """
        return not self._work_queue.empty()
