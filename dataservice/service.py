import asyncio
from logging import getLogger
from typing import Generator, Iterable, Optional, AsyncGenerator, AsyncIterator

from tenacity import retry

from dataservice.client import Client
from dataservice.models import Request

MAX_ASYNC_TASKS = 10

logger = getLogger(__name__)

class DataService:
    def __init__(self, requests: Iterable[Request], clients: tuple[Client], max_async_tasks: Optional[int] = MAX_ASYNC_TASKS):
        self.clients = clients
        self.__queue = asyncio.Queue()
        self.__data = asyncio.Queue()
        self.max_async_tasks = max_async_tasks
        self._start_requests = iter(requests)

    @property
    def client(self) -> Client:
        return self.clients[0]

    def __aiter__(self):
        return self

    async def __anext__(self) -> AsyncIterator[dict]:
        # this will only run once
        for request in self._start_requests:
            await self.__queue.put(request)

        async with asyncio.Semaphore(self.max_async_tasks):
            items = []
            while not self.__queue.empty() and len(items) < MAX_ASYNC_TASKS:
                items.append(await self.__queue.get())
            tasks = [processed_item for item in items async for processed_item in self._process_item(item)]
            await asyncio.gather(*tasks)
            for t in tasks:
                if t.result() is not None:
                    await self.__data.put(t.result())
            if not self.__data.empty():
                return await self.__data.get()

        if self.__queue.empty():
            raise StopAsyncIteration

    async def _handle_queue_item(self, item: Request | dict) -> Optional[dict]:
        if isinstance(item, Request):
            response = await self._handle_request(item)
            parsed = item.callback(response)
            if isinstance(parsed, dict):
                return parsed
            await self.__queue.put(parsed)
        elif isinstance(item, dict):
            return item
        else:
            raise ValueError(f"Unknown item type: {type(item)}")

    @retry
    async def _handle_request(self, item: Request):
        """Make a request using the client and retry if necessary."""
        return await self.client.make_request(item)

    async def _process_item(self, item: Request | Generator | AsyncGenerator) -> AsyncGenerator[asyncio.Task, None]:
        if isinstance(item, Generator):
            for i in item:
                yield asyncio.create_task(self._handle_queue_item(i))
        elif isinstance(item, AsyncGenerator):
            async for i in item:
                yield asyncio.create_task(self._handle_queue_item(i))
        else:
            yield asyncio.create_task(self._handle_queue_item(item))



