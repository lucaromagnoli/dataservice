from __future__ import annotations

import asyncio
import logging
from dataclasses import is_dataclass
from typing import Any, AsyncGenerator, Generator

from dataservice.models import Request, Response, RequestsIterable

logger = logging.getLogger(__name__)


class DataWorker:
    """
    A worker class to handle asynchronous data processing.
    """

    _clients: dict[Any, Any] = {}

    def __init__(self, requests: RequestsIterable, config: dict[str, Any]):
        """
        Initializes the DataWorker with the given parameters.
        """
        self._max_workers: int = config["max_workers"]
        self._deduplication: bool = config["deduplication"]
        self._deduplication_keys: tuple = config["deduplication_keys"]
        self._requests: RequestsIterable = requests
        self._work_queue: asyncio.Queue = asyncio.Queue()
        self._data_queue: asyncio.Queue = asyncio.Queue()
        self._seen_requests: set = set()
        self._started: bool = False

    async def _get_batch_items_from_queue(
        self,
    ) -> list[RequestsIterable | Request | dict]:
        """
        Retrieves a batch of items from the work queue.
        """
        items: list[RequestsIterable | Request | dict] = []
        while not self._work_queue.empty() and len(items) < self._max_workers:
            items.append(await self._work_queue.get())
        return items

    async def _add_to_work_queue(self, item: RequestsIterable | Request) -> None:
        """
        Adds an item to the work queue.
        """
        await self._work_queue.put(item)

    async def _add_to_data_queue(self, item: dict) -> None:
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

    async def _handle_queue_item(self, item: Request | dict) -> None:
        """
        Handles an item from the work queue.
        """
        if isinstance(item, Request):
            await self._handle_request_item(item)
        elif isinstance(item, dict) or is_dataclass(item):
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
        if response is None:
            return

        callback_result = request.callback(response)
        if isinstance(callback_result, dict):
            await self._add_to_data_queue(callback_result)
        else:
            await self._add_to_work_queue(callback_result)

    @classmethod
    async def _handle_request(cls, request: Request) -> Response:
        """
        Makes an asynchronous request.
        """
        key = str(request.client)
        if key not in cls._clients:
            cls._clients[key] = request.client

        client = cls._clients[key]
        response = await client(request)
        if response.status_code == 200:
            return response

    async def _iter_callbacks(self, item: Any) -> AsyncGenerator[asyncio.Task, None]:
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
            async with asyncio.Semaphore(self._max_workers):
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
