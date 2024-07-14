import asyncio
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from logging import getLogger
from typing import Callable, Generator, Iterable, Type, Any, Optional

from dataservice.client import Client
from dataservice.models import Request, Response

MAX_ASYNC_TASKS = 10

logger = getLogger(__name__)


class DataService:
    """Data Service class that orchestrates the Request - Response data flow."""

    def __init__(
        self,
        clients: tuple[Client],
        pipeline: Optional[Callable[[list], None]] = None,
    ):
        self.clients = clients
        self.pipeline = pipeline
        self.queue = asyncio.Queue()
        self.data = []
        self.MAX_ASYNC_TASKS = MAX_ASYNC_TASKS

    def __call__(self, requests_iterable: Iterable[Request]):
        """Main entry point. This method is called by the client."""
        return asyncio.run(self._fetch(requests_iterable))

    @property
    def client(self):
        return self.clients[0]

    async def handle_queue_item(self, item: Request, data: list):
        if isinstance(item, Request):
            response = await self.client.make_request(item)
            parsed = item.callback(response)
            await self.queue.put(parsed)
        elif isinstance(item, dict):
            data.append(item)
        else:
            raise ValueError(f"Unknown item type: {type(item)}")

    async def get_batch_items_from_queue(self, max_items: int = MAX_ASYNC_TASKS):
        items = []
        while not self.queue.empty():
            item = await self.queue.get()
            items.append(item)
            if len(items) == max_items:
                return items
        return items

    async def _fetch(self, requests_iterable: Iterable[Request]) -> list[dict]:
        """
        The main Data Service data gathering logic. Passes initial requests iterable to client
        and starts the Request-Response data flow until there are no more Requests and Responses to process.
        """
        data = []

        # Enqueue initial requests
        for request in requests_iterable:
            await self.queue.put(request)

        semaphore = asyncio.Semaphore(self.MAX_ASYNC_TASKS)

        while not self.queue.empty():
            items = await self.get_batch_items_from_queue()
            tasks = [self._process_item(item, data, semaphore) for item in items]
            await asyncio.gather(*tasks)

        return data

    async def _process_item(self, item: Request | Generator, data: list[Response], semaphore: asyncio.Semaphore):
        """
        Process a single item from the queue, handling generators appropriately.
        """
        if isinstance(item, Generator):
            async with semaphore:
                for i in item:
                    await self.handle_queue_item(i, data)
        else:
            async with semaphore:
                await self.handle_queue_item(item, data)


