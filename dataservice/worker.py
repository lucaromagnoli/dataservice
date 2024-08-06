"""Handles the actual data processing tasks, including managing queues, handling requests, and processing data items."""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import is_dataclass
from typing import TYPE_CHECKING, Any, AsyncGenerator, Generator

from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from dataservice.data import DataWrapper
from dataservice.config import ServiceConfig
from dataservice.exceptions import (
    RequestException,
    RetryableRequestException,
    ParsingException,
)
from dataservice.models import FailedRequest, Request, RequestsIterable, Response

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

logger = logging.getLogger(__name__)


class DataWorker:
    """
    A worker class to handle asynchronous data processing.
    """

    _clients: dict[Any, Any] = {}

    def __init__(self, requests: RequestsIterable, config: ServiceConfig):
        """
        Initializes the DataWorker with the given parameters.
        """
        self.config = config
        self._requests: RequestsIterable = requests
        self._work_queue: asyncio.Queue = asyncio.Queue()
        self._data_queue: asyncio.Queue = asyncio.Queue()
        self._failures: list[FailedRequest] = []
        self._seen_requests: set = set()
        self._started: bool = False

    async def _add_to_work_queue(self, item: RequestsIterable | Request) -> None:
        """
        Adds an item to the work queue.
        """
        await self._work_queue.put(item)

    async def _add_to_data_queue(
        self, item: dict | type[DataclassInstance] | DataWrapper
    ) -> None:
        """
        Adds an item to the data queue.
        """
        await self._data_queue.put(item)

    def _add_to_failures(self, item: FailedRequest) -> None:
        """
        Adds an item to the failures list.
        """
        self._failures.append(item)

    async def _enqueue_start_requests(self) -> None:
        """
        Enqueues the initial set of requests to the work queue.
        """
        if isinstance(self._requests, AsyncGenerator):
            async for request in self._requests:
                await self._add_to_work_queue(request)
        else:
            for request in self._requests:
                await self._add_to_work_queue(request)
        if self._work_queue.empty():
            raise ValueError("No requests to process.")
        self._started = True

    async def _handle_queue_item(
        self, item: Request | dict | type[DataclassInstance] | DataWrapper
    ) -> None:
        """
        Handles an item from the work queue.
        """
        if isinstance(item, Request):
            await self._handle_request_item(item)
        elif isinstance(item, (dict, DataWrapper)) or is_dataclass(item):
            await self._add_to_data_queue(item)
        else:
            raise ValueError(f"Unknown item type {type(item)}")

    def _is_duplicate_request(self, request: Request) -> bool:
        """
        Checks if a request is a duplicate.
        """
        key = request.url
        if key in self._seen_requests:
            return True
        self._seen_requests.add(key)
        return False

    async def _handle_request_item(self, request: Request) -> None:
        """
        Handles a request item.
        """
        if self.config.deduplication and self._is_duplicate_request(request):
            return
        try:
            response = await self._handle_request(request)
            callback_result = await self._handle_callback(request, response)
            if isinstance(callback_result, (dict, DataWrapper)) or is_dataclass(
                callback_result
            ):
                await self._add_to_data_queue(callback_result)
            else:
                await self._add_to_work_queue(callback_result)
        except (RequestException, ParsingException) as e:
            logger.error(f"An exception occurred: {e}")
            self._add_to_failures({"request": request, "error": str(e)})
            return

    async def _handle_callback(self, request, response):
        """Handles the callback function of a request."""
        try:
            return request.callback(response)
        except Exception as e:
            logger.error(f"Error processing callback {request.callback.__name__}: {e}")
            raise ParsingException(
                f"Error processing callback {request.callback.__name__}: {e}"
            )

    async def _handle_request(self, request: Request) -> Response:
        """
        Makes an asynchronous request and retry on 500 status code.
        """
        key = type(request.client).__name__.lower()
        if key not in self._clients:
            self._clients[key] = request.client
        client = self._clients[key]
        await asyncio.sleep(random.randint(0, self.config.random_delay) / 1000)
        return await self._wrap_retry(client, request)

    async def _wrap_retry(self, client, request):
        """Wraps the request in a retry mechanism."""

        def before_log(logger):
            def _before_log(retry_state):
                logger.debug(
                    f"Retrying request {request.url}, attempt {retry_state.attempt_number}",
                )

            return _before_log

        def after_log(logger):
            def _after_log(retry_state):
                logger.debug(
                    f"Retry attempt {retry_state.attempt_number}. Request {request.url} returned with status {retry_state.outcome}",
                )

            return _after_log

        retryer = AsyncRetrying(
            reraise=True,
            stop=stop_after_attempt(self.config.retry.max_attempts),
            wait=wait_exponential(
                multiplier=self.config.retry.wait_exp_mul,
                min=self.config.retry.wait_exp_min,
                max=self.config.retry.wait_exp_max,
            ),
            retry=retry_if_exception_type(RetryableRequestException),
            before=before_log(logger),
            after=after_log(logger),
        )
        return await retryer(self._make_request, client, request)

    @staticmethod
    async def _make_request(client, request) -> Response:
        """Wraps client call."""
        return await client(request)

    async def _iter_callbacks(self, item: Any) -> AsyncGenerator[asyncio.Task, None]:
        """
        Iterates over callbacks and creates tasks for them.
        """
        if isinstance(item, Generator):
            for i in item:
                yield asyncio.create_task(self._handle_queue_item(i))
        elif isinstance(item, AsyncGenerator):
            async for i in item:
                yield asyncio.create_task(self._handle_queue_item(i))
        elif isinstance(item, (Request, dict)) or is_dataclass(item):
            yield asyncio.create_task(self._handle_queue_item(item))
        else:
            raise ValueError(f"Unknown item type {type(item)}")

    async def fetch(self) -> None:
        """
        Fetches data items by processing the work queue.
        """
        semaphore = asyncio.Semaphore(self.config.max_concurrency)
        async with semaphore:
            if not self._started:
                await self._enqueue_start_requests()
            while self.has_jobs():
                logger.debug(f"Work queue size: {self._work_queue.qsize()}")
                item = self._work_queue.get_nowait()
                tasks = [task async for task in self._iter_callbacks(item)]
                await asyncio.gather(*tasks)

    def get_data_item(self) -> Any:
        """
        Retrieve a data item from the data queue.
        """
        return self._data_queue.get_nowait()

    def has_no_more_data(self) -> bool:
        """
        Check if there are no more data items in the data queue.
        """
        return self._data_queue.empty()

    def has_jobs(self) -> bool:
        """
        Check if there are jobs in the work queue.
        """
        return not self._work_queue.empty()

    def get_failures(self) -> tuple[FailedRequest, ...]:
        """
        Return a tuple of failed requests.
        """
        return tuple(self._failures)
