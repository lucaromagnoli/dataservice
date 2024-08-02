import asyncio
import os
from logging import getLogger
from typing import AsyncGenerator, Generator

from tenacity import retry

from dataservice.client import Client
from dataservice.models import Request, RequestOrData, RequestsIterable

MAX_ASYNC_TASKS = int(os.environ.get("MAX_ASYNC_TASKS", "10"))
logger = getLogger(__name__)


class DataService:
    """Data Service class that orchestrates the Request - Response data flow."""

    def __init__(
        self,
        requests: RequestsIterable,
        clients: list[Client] | tuple[Client],
        max_async_tasks: int = MAX_ASYNC_TASKS,
    ):
        self.clients = clients
        self.max_async_tasks = max_async_tasks
        self._requests: RequestsIterable = requests
        self.__work_queue: asyncio.Queue[RequestsIterable | Request] = asyncio.Queue()
        self.__data_queue: asyncio.Queue[dict] = asyncio.Queue()
        self.__started: bool = False

    def __aiter__(self):
        logger.info("Starting Data Service")
        return self

    async def __anext__(self):
        """Return the next item from the data queue."""
        await self._fetch()
        if self.__data_queue.empty():
            raise StopAsyncIteration
        return self.__data_queue.get_nowait()

    @property
    def client(self) -> Client:
        """Return the primary client."""
        return self.clients[0]

    def _get_client_by_name(self, name: str | None) -> Client:
        """Return the client by name."""
        if name is None:
            return self.client
        for client in self.clients:
            if client.get_name() == name:
                return client
        raise ValueError(f"Client not found: {name}")

    async def _get_batch_items_from_queue(self) -> list[RequestsIterable | Request]:
        """Get a batch of items from the queue."""
        items: list[RequestsIterable | Request] = []
        while not self.__work_queue.empty() and len(items) < self.max_async_tasks:
            item = await self.__work_queue.get()
            items.append(item)
        return items

    async def _add_to_work_queue(self, item: RequestsIterable | Request) -> None:
        """Add an item to the work queue."""
        await self.__work_queue.put(item)

    async def _add_to_data_queue(self, item: dict) -> None:
        """Add an item to the data queue."""
        await self.__data_queue.put(item)

    async def _enqueue_start_requests(self):
        """Enqueue the initial requests to the work queue."""
        if isinstance(self._requests, AsyncGenerator):
            async for request in self._requests:
                await self._add_to_work_queue(request)
        else:
            for request in self._requests:
                await self._add_to_work_queue(request)
        if self.__work_queue.empty():
            raise ValueError("No requests to process.")
        self.__started = True

    async def _handle_queue_item(self, item: RequestOrData) -> None:
        """Handle a single item from the queue and run callback over the response."""
        if isinstance(item, Request):
            return await self._handle_request_item(item)
        elif isinstance(item, dict):
            return await self._add_to_data_queue(item)
        else:
            raise ValueError(f"Unknown item type {type(item)}")

    async def _handle_request_item(self, request: Request) -> None:
        """Handle a single Request and run callback over the response."""
        client = self._get_client_by_name(request.client)
        response = await client.make_request(request)
        callback_result = request.callback(response)
        if isinstance(callback_result, dict):
            return await self._add_to_data_queue(callback_result)
        else:  # callback_result is a Request or a Generator or AsyncGenerator
            return await self._add_to_work_queue(callback_result)

    async def _iter_callbacks(
        self, item: Generator | AsyncGenerator | RequestOrData
    ) -> AsyncGenerator[asyncio.Task, None]:
        """
        Iterates over the items yielded by the callback functions and handles them accordingly.
        Returns an async iterator of asyncio Tasks.
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

    async def _fetch(self) -> None:
        """
        The main Data Service data gathering logic. Enqueues the initial requests
        and starts the Request-Response data flow until there are no more Requests to process.
        """
        if not self.__started:
            await self._enqueue_start_requests()

        while not self.__work_queue.empty():
            logger.debug(f"Work queue size: {self.__work_queue.qsize()}")
            async with asyncio.Semaphore(self.max_async_tasks):
                items = await self._get_batch_items_from_queue()
                tasks = [
                    task for item in items async for task in self._iter_callbacks(item)
                ]
                await asyncio.gather(*tasks)
