"""
DataService: Manages the overall data processing service, including initialization, iteration, and running the data worker.
DataWorker: Handles the actual data processing tasks, including managing queues, handling requests, and processing data items.
"""
from __future__ import annotations
import asyncio
import os
from logging import getLogger
from typing import Any, Optional

from dataservice.models import RequestsIterable
from dataservice.worker import DataWorker
from dataservice.pipeline import Pipeline

MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "10"))
logger = getLogger(__name__)

__all__ = ["DataService"]


class DataService:
    """
    A service class to handle data requests and processing.
    """

    def __init__(
        self, requests: RequestsIterable, config: Optional[dict[str, Any]] = None
    ):
        """
        Initializes the DataService with the given parameters.
        """
        default_config = {
            "max_workers": MAX_WORKERS,
            "deduplication": True,
            "deduplication_keys": ("url",),
        }
        self._requests = requests
        self._config = {**default_config, **(config or {})}
        self._data_worker: DataWorker | None = None

    @property
    def config(self) -> dict[str, Any]:
        """
        Returns the configuration dictionary.
        """
        return self._config

    @property
    def data_worker(self) -> DataWorker:
        """
        Lazy initialization of the DataWorker instance.
        """
        if self._data_worker is None:
            self._data_worker = DataWorker(self._requests, self.config)
        return self._data_worker

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
