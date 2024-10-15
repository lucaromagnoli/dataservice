"""
Manages the overall data processing service, including initialization, iteration, and running the data worker.
"""

from __future__ import annotations

import asyncio
import pathlib
from logging import getLogger
from typing import Any, Iterable

from pydantic import BaseModel, validate_call

from dataservice.config import ServiceConfig
from dataservice.files import writers
from dataservice.models import FailedRequest, Request
from dataservice.worker import DataWorker

logger = getLogger(__name__)


class DataService:
    """
    A service class to handle data requests and processing.
    """

    def __init__(
        self, requests: Iterable[Request], config: ServiceConfig = ServiceConfig()
    ):
        """
        Initializes the DataService with the given parameters.

        :param requests: An iterable of requests to process.
        :param config: The configuration for the service.

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

        self._requests: Iterable[Request] = requests
        self.config: ServiceConfig = config
        self._data_worker: DataWorker = DataWorker(self._requests, self.config)

    def get_failures(self) -> dict[str, FailedRequest]:
        """
        Returns a dict of failed requests.
        """
        return self._data_worker.get_failures()

    def __iter__(self) -> DataService:
        """
        Returns the iterator object itself.
        """
        return self

    def __next__(self) -> Any:
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

    @validate_call
    def write(
        self,
        filepath: pathlib.Path,
        results: Iterable[dict | BaseModel] | None = None,
    ) -> None:
        """
        Writes the results to a file.

        :param results: An iterable of data items to write.
        :param filepath: The path to the output file.
        """
        ext = filepath.suffix
        writer = writers[ext[1:]]
        if results is None:
            results = self
        writer(filepath).write(results)
