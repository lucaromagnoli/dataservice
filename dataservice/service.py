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
        max_async_tasks: Optional[int] = MAX_ASYNC_TASKS,
    ):
        self.clients = clients
        self.max_async_tasks = max_async_tasks
        self.__work_queue: asyncio.Queue[Request | Response] = asyncio.Queue()
        self.__data_queue: asyncio.Queue[dict] = asyncio.Queue()
        self.__started: bool = False
        self._requests: RequestsIterable = requests

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

    async def _handle_request_item(self, request: Request) -> None:
        """Handle a single Request item from the queue and run callback over the response."""
        response = await self._handle_request(request)
        parsed = request.callback(response)
        if isinstance(parsed, dict):
            await self.__data_queue.put(parsed)
        else:
            await self.__work_queue.put(parsed)

    @retry
    async def _handle_request(self, request: Request):
        """Handle a single Request with retry."""
        client = self._get_client_by_name(request.client)
        response = await client.make_request(request)
        return response

    async def _get_batch_items_from_queue(
        self, max_items: int = MAX_ASYNC_TASKS
    ) -> list:
        """Get a batch of items from the queue."""
        items = []
        while not self.__work_queue.empty() and len(items) < max_items:
            item = await self.__work_queue.get()
            items.append(item)
        return items

    async def _iter_callbacks(
        self, item: Request | Generator | AsyncGenerator
    ) -> AsyncGenerator[asyncio.Task, None]:
        """
        Iterates over the items yielded by the callback functions and handles them accordingly.
        """
        if isinstance(item, Generator):
            for i in item:
                yield asyncio.create_task(self._handle_request_item(i))
        elif isinstance(item, AsyncGenerator):
            async for i in item:
                yield asyncio.create_task(self._handle_request_item(i))
        else:
            yield asyncio.create_task(self._handle_request_item(item))

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
