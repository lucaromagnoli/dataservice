"""
Manages the overall data processing service, including initialization, iteration, and running the data worker.
"""

from __future__ import annotations

import asyncio
import pathlib
from abc import ABC
from logging import getLogger
from typing import AsyncIterator, Iterable, Iterator

from pydantic import BaseModel, validate_call

from dataservice.config import ServiceConfig
from dataservice.files import writers
from dataservice.models import FailedRequest, GenericDataItem, Request
from dataservice.worker import DataWorker

logger = getLogger(__name__)


class BaseDataService(ABC):
    """A base class for the data service."""

    def __init__(
        self, requests: Iterable[Request], config: ServiceConfig = ServiceConfig()
    ):
        self._requests: Iterable[Request] = requests
        self.config: ServiceConfig = config
        self._data_worker: DataWorker = DataWorker(self._requests, self.config)

    def get_failures(self) -> dict[str, FailedRequest]:
        """
        Returns a dict of failed requests.
        """
        return self._data_worker.get_failures()

    @validate_call
    def write(
        self,
        filepath: pathlib.Path,
        results: Iterable[dict | BaseModel],
    ) -> None:
        """
        Writes the results to a file.

        :param results: An iterable of data items to write.
        :param filepath: The path to the output file.
        """
        ext = filepath.suffix
        writer = writers[ext[1:]]
        writer(filepath).write(results)


class DataService(BaseDataService):
    """
    A service class to handle data requests and processing.
    This is the synchronous version of the data service. It will run the data worker in the main thread
    and block until all data items are fetched.

    :Example:
    .. code-block:: python

    from dataservice import DataService, HttpXClient, Request, Response

    def parse_books_page(response: Response):
        articles = response.html.find_all("article", {"class": "product_pod"})
        return {
            "url": response.request.url,
            "title": response.html.title.get_text(strip=True),
            "articles": len(articles)
        }

    start_requests = [Request(url="https://books.toscrape.com/index.html", callback=parse_books_page, client=HttpXClient())]
    service = DataService(start_requests)
    for data_item in service:
        print(data_item)
    """

    def __iter__(self) -> Iterator[GenericDataItem]:
        """
        Returns the iterator object itself.
        """
        return self

    def __next__(self) -> GenericDataItem:
        """
        Fetches the next data item from the data worker.
        """
        if not self._data_worker.has_started:
            asyncio.run(self._data_worker.fetch())
        if self._data_worker.has_no_more_data():
            raise StopIteration
        return self._data_worker.get_data_item()

    def _run_data_worker(self) -> None:
        """
        Runs the data worker to fetch data items.
        """
        asyncio.run(self._data_worker.fetch())


class AsyncDataService(BaseDataService):
    """An asynchronous version of the data service.
    This class is an asynchronous iterator that can be used to fetch data items asynchronously.

    :Example:
    .. code-block:: python

    from dataservice import AsyncDataService, HttpXClient, Request, Response

    def parse_books_page(response: Response):
        articles = response.html.find_all("article", {"class": "product_pod"})
        return {
            "url": response.request.url,
            "title": response.html.title.get_text(strip=True),
            "articles": len(articles)
        }

    async def main():
        start_requests = [Request(url="https://books.toscrape.com/index.html", callback=parse_books_page, client=HttpXClient())]
        service = AsyncDataService(start_requests)
        async for data_item in service:
            print(data_item)

    asyncio.run(main())
    """

    def __aiter__(self) -> AsyncIterator[GenericDataItem]:
        """Returns the asynchronous iterator object itself."""
        return self

    async def __anext__(self) -> GenericDataItem:
        """Fetches the next data item from the data worker."""
        if not self._data_worker.has_started:
            await self._data_worker.fetch()
        if self._data_worker.has_no_more_data():
            raise StopAsyncIteration
        return self._data_worker.get_data_item()

    async def _run_data_worker(self) -> None:
        await self._data_worker.fetch()
