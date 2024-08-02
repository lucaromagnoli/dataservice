import asyncio
import os
from logging import getLogger
from typing import AsyncGenerator, Generator, Iterable, Optional

from tenacity import retry

from dataservice.client import Client
from dataservice.models import Request, Response

MAX_ASYNC_TASKS = int(os.environ.get("MAX_ASYNC_TASKS", "10"))
logger = getLogger(__name__)

RequestsIterable = (
    Iterable[Request] | Generator[Request, None, None] | AsyncGenerator[Request, None]
)


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

    def _get_client_by_name(self, name: str) -> Client:
        """Return the client by name."""
        for client in self.clients:
            if client.get_name() == name:
                return client
        raise ValueError(f"Client not found: {name}")

    async def _get_batch_items_from_queue(
            self, max_items: int = MAX_ASYNC_TASKS
    ) -> list[RequestsIterable | Request]:
        """Get a batch of items from the queue."""
        items: list[RequestsIterable | Request] = []
        while not self.__work_queue.empty() and len(items) < max_items:
            item = await self.__work_queue.get()
            items.append(item)
        return items

    async def _enqueue_requests(self):
        """Enqueue the initial requests to the work queue."""
        if isinstance(self._requests, AsyncGenerator):
            async for request in self._requests:
                await self.__work_queue.put(request)
        else:
            for request in self._requests:
                await self.__work_queue.put(request)
        if self.__work_queue.empty():
            raise ValueError("No requests to process.")
        self.__started = True

    async def _handle_queue_item(self, request: Request | dict) -> None:
        """Handle a single item from the queue and run callback over the response."""
        if isinstance(request, Request):
            return await self._handle_request_item(request)
        elif isinstance(request, dict):
            return await self.__data_queue.put(request)
        else:
            raise ValueError(f"Unknown item type {type(request)}")

    async def _handle_request_item(self, request: Request) -> None:
        """Handle a single Request and run callback over the response."""
        response = await self._handle_request(request)
        callback_result = request.callback(response)
        if isinstance(callback_result, dict):
            return await self.__data_queue.put(callback_result)
        if isinstance(callback_result, Request):
            return await self.__work_queue.put(callback_result)
        elif isinstance(callback_result, (Iterable, Generator, AsyncGenerator)):
            return await self.__work_queue.put(callback_result)

    @retry
    async def _handle_request(self, request: Request) -> Response:
        """Handle a single Request with retry."""
        client = self._get_client_by_name(request.client)
        return await client.make_request(request)


    async def _iter_callbacks(
        self, item: RequestsIterable | Request
    ) -> AsyncGenerator[asyncio.Task, None]:
        """
        Iterates over the items yielded by the callback functions and handles them accordingly.
        """
        print(type(item))
        if isinstance(item, Generator):
            for i in item:
                yield asyncio.create_task(self._handle_queue_item(i))
        elif isinstance(item, AsyncGenerator):
            async for i in item:
                yield asyncio.create_task(self._handle_queue_item(i))
        elif isinstance(item, Request):
            yield asyncio.create_task(self._handle_queue_item(item))
        elif isinstance(item, dict):
            yield await self.__data_queue.put(item)

        else:
            raise ValueError(f"Unknown item type {type(item)}")

    async def _fetch(self) -> None:
        """
        The main Data Service data gathering logic. Enqueues the initial requests
        and starts the Request-Response data flow until there are no more Requests to process.
        """
        if not self.__started:
            await self._enqueue_requests()

        while not self.__work_queue.empty():
            async with asyncio.Semaphore(self.max_async_tasks):
                items = await self._get_batch_items_from_queue()
                tasks = [
                    callback_item
                    for item in items
                    async for callback_item in self._iter_callbacks(item)
                ]
                await asyncio.gather(*tasks)

