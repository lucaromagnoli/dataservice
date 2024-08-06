"""
Manages the overall data processing service, including initialization, iteration, and running the data worker.
"""

from __future__ import annotations

import asyncio
from logging import getLogger
from typing import Any

from dataservice.config import ServiceConfig
from dataservice.models import FailedRequest, RequestsIterable
from dataservice.worker import DataWorker

logger = getLogger(__name__)


class DataService:
    """
    A service class to handle data requests and processing.
    """

    def __init__(
        self, requests: RequestsIterable, config: ServiceConfig = ServiceConfig()
    ):
        """
        Initializes the DataService with the given parameters.
        :param requests: An iterable of requests to process.
        :param config: The configuration for the service.
        """

        self._requests = requests
        self.config = config
        self._data_worker: DataWorker | None = None

    @property
    def data_worker(self) -> DataWorker:
        """
        Lazy initialization of the DataWorker instance.
        """
        if self._data_worker is None:
            self._data_worker = DataWorker(self._requests, self.config)
        return self._data_worker

    @property
    def failures(self) -> tuple[FailedRequest, ...]:
        """
        Returns the list of failed requests.
        """
        return self.data_worker.get_failures()

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
