import asyncio
from logging import getLogger
from typing import Callable, Generator, Iterable, Optional, AsyncGenerator

from dataservice.client import Client
from dataservice.models import Request

MAX_ASYNC_TASKS = 10

logger = getLogger(__name__)


class DataService:
    """Data Service class that orchestrates the Request - Response data flow."""

    def __init__(
        self,
        clients: tuple[Client],
    ):
        self.clients = clients
        self.queue = asyncio.Queue()
        self.MAX_ASYNC_TASKS = MAX_ASYNC_TASKS

    def __call__(self, requests_iterable: Iterable[Request]):
        """Main entry point. This method is called by the client."""
        return asyncio.run(self._fetch(requests_iterable))

    @property
    def client(self):
        return self.clients[0]

    async def handle_queue_item(self, item: Request):
        if isinstance(item, Request):
            response = await self.client.make_request(item)
            parsed = item.callback(response)
            if isinstance(parsed, dict):
                return parsed
            await self.queue.put(parsed)
        elif isinstance(item, dict):
            return item
        else:
            raise ValueError(f"Unknown item type: {type(item)}")

    async def get_batch_items_from_queue(self, max_items: int = MAX_ASYNC_TASKS):
        items = []
        while not self.queue.empty():
            item = await self.queue.get()
            items.append(item)
            if len(items) == max_items:
                return items
        return

    async def _process_item(
        self, item: Request | Generator
    ) -> AsyncGenerator[asyncio.Task, None]:
        """
        Process a single item from the queue, handling generators appropriately.
        """
        if isinstance(item, Generator):
            for i in item:
                yield asyncio.create_task(self.handle_queue_item(i))
        elif isinstance(item, AsyncGenerator):
            async for i in item:
                yield asyncio.create_task(self.handle_queue_item(i))
        else:
            yield asyncio.create_task(self.handle_queue_item(item))

    async def _fetch(self, requests_iterable: Iterable[Request]) -> list[dict]:
        """
        The main Data Service data gathering logic. Passes initial requests iterable to client
        and starts the Request-Response data flow until there are no more Requests and Responses to process.
        """
        data = []

        # Enqueue initial requests
        for request in requests_iterable:
            await self.queue.put(request)

        while not self.queue.empty():
            async with asyncio.Semaphore(self.MAX_ASYNC_TASKS):
                items = await self.get_batch_items_from_queue()
                tasks = [
                    processed_item
                    for item in items
                    async for processed_item in self._process_item(item)
                ]
                await asyncio.gather(*tasks)
                data = [*data, *[t.result() for t in tasks if t.result() is not None]]
        return data
