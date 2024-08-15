"""
Manages the overall data processing service, including initialization, iteration, and running the data worker.
"""

from __future__ import annotations

import asyncio
import pathlib
from concurrent.futures import ProcessPoolExecutor
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
    def failures(self) -> dict[str, FailedRequest]:
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
        if not self.data_worker.has_started:
            with ProcessPoolExecutor() as executor:
                asyncio.get_event_loop().run_in_executor(
                    executor,
                    self._run_data_worker(),  # type: ignore
                )
        if self.data_worker.has_no_more_data():
            raise StopIteration
        return self.data_worker.get_data_item()

    def _run_data_worker(self) -> None:
        """
        Runs the data worker to fetch data items.
        """
        asyncio.run(self.data_worker.fetch())

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
