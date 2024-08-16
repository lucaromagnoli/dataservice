"""Handles the actual data processing tasks, including managing queues, handling requests, and processing data items."""

from __future__ import annotations

import asyncio
import logging
import random
from concurrent.futures.thread import ThreadPoolExecutor
from contextlib import nullcontext
from pathlib import Path
from typing import Any, AsyncGenerator, Generator, Iterable, cast

from aiolimiter import AsyncLimiter
from pydantic import BaseModel
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from dataservice.cache import AsyncJsonCache, cache_request
from dataservice.config import ServiceConfig
from dataservice.exceptions import (
    DataServiceException,
    ParsingException,
    RetryableException,
)
from dataservice.models import ClientCallable, FailedRequest, Request, Response

logger = logging.getLogger(__name__)


class DataWorker:
    """
    A worker class to handle asynchronous data processing.
    """

    _clients: dict[Any, Any] = {}

    def __init__(
        self,
        requests: Iterable[Request],
        config: ServiceConfig,
    ):
        """
        Initializes the DataWorker with the given parameters.
        :param requests: An iterable of requests to process.
        :param config: The configuration for the service.
        """
        self.config: ServiceConfig = config
        self._requests: Iterable[Request] = requests
        self._data_queue: asyncio.Queue = asyncio.Queue()
        self._work_queue: asyncio.Queue = asyncio.Queue()
        self._failures: dict[str, FailedRequest] = {}
        self._seen_requests: set = set()
        self._started: bool = False
        self._cache: AsyncJsonCache | None = None
        self._limiter: AsyncLimiter | None = None

    @property
    def limiter_context(self):
        if self.limiter is not None:
            return self.limiter
        return nullcontext()

    @property
    def limiter(self):
        if self._limiter is None and self.config.limiter is not None:
            self._limiter = AsyncLimiter(
                self.config.limiter.max_rate, self.config.limiter.time_period
            )
        return self._limiter

    @property
    def cache_context(self):
        return self.cache if self.config.cache.use else nullcontext()

    @property
    def has_started(self) -> bool:
        """
        Check if the worker has started.

        :return: True if the worker has started, False otherwise.
        """
        return self._started

    @property
    def cache(self) -> AsyncJsonCache | None:
        """
        Lazy initialization of the cache instance.
        """
        if self._cache is None and self.config.cache.use:
            self._cache = AsyncJsonCache(Path(self.config.cache.path))
        return self._cache

    async def _add_to_work_queue(self, item: Iterable[Request] | Request) -> None:
        """
        Adds an item to the work queue.

        :param item: The item to add to the work queue.
        """
        await self._work_queue.put(item)

    async def _add_to_data_queue(self, item: dict | BaseModel) -> None:
        """
        Adds an item to the data queue.

        :param item: The item to add to the data queue.
        """
        await self._data_queue.put(item)

    def _add_to_failures(self, failed_req: FailedRequest) -> None:
        """
        Adds an item to the failures list.

        :param failed_req: The failed request to add to the failures list.
        """
        request: Request = failed_req["request"]
        self._failures[str(request.url)] = failed_req

    def get_data_item(self) -> dict | BaseModel:
        """
        Retrieve a data item from the data queue.

        :return: The data item.
        """
        return self._data_queue.get_nowait()

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

    async def _handle_queue_item(self, item: Request | dict | BaseModel) -> None:
        """
        Handles an item from the work queue.

        :param item: The item to handle from the work queue.
        """
        if isinstance(item, Request):
            await self._handle_request_item(item)
        elif isinstance(item, (dict, BaseModel)):
            await self._add_to_data_queue(item)
        else:
            raise ValueError(f"Unknown item type {type(item)}")

    def _is_duplicate_request(self, request: Request) -> bool:
        """
        Checks if a request is a duplicate.

        :param request: The request to check for duplication.
        :return: True if the request is a duplicate, False otherwise.
        """
        key = request.model_dump_json(include=self.config.deduplication_keys)
        if key in self._seen_requests:
            return True
        self._seen_requests.add(key)
        return False

    def _has_request_failed(self, request: Request) -> bool:
        """
        Checks if a request has failed.

        :param request: The request to check for failure.
        :return: True if the request has failed, False otherwise.
        """
        return request.url in self._failures

    async def _handle_request_item(self, request: Request) -> None:
        """
        Handles a request item.

        :param request: The request item to handle.
        """
        if self.config.deduplication and self._is_duplicate_request(request):
            return
        if self._has_request_failed(request):
            logger.debug(f"Skipping failed request {request.url}")
            return
        async with self.limiter_context:
            try:
                response = await self._handle_request(request)
                callback_result = await self._handle_callback(request, response)
                if isinstance(callback_result, (dict, BaseModel)):
                    await self._add_to_data_queue(callback_result)
                else:
                    await self._add_to_work_queue(callback_result)
            except (DataServiceException, ParsingException) as e:
                logger.error(f"An exception occurred: {e}")
                self._add_to_failures(
                    {
                        "request": request,
                        "message": str(e),
                        "exception": type(e).__name__,
                    }
                )
                return

    async def _handle_callback(self, request, response):
        """
        Handles the callback function of a request.

        :param request: The request object.
        :param response: The response object.
        :return: The result of the callback function.
        """
        try:
            with ThreadPoolExecutor() as executor:
                return await asyncio.get_event_loop().run_in_executor(
                    executor, request.callback, response
                )
        except Exception as e:
            logger.error(f"Error processing callback {request.callback_name}: {e}")
            raise ParsingException(
                f"Error processing callback {request.callback_name}: {e}"
            )

    async def _handle_request(self, request: Request) -> Response:
        """
        Makes an asynchronous request and retry on 500 status code.

        :param request: The request object.
        :return: The response object.
        """
        key = request.client_name
        if key not in self._clients:
            self._clients[key] = request.client
        client = self._clients[key]
        if self.config.constant_delay:
            await asyncio.sleep(self.config.constant_delay / 1000)
        if self.config.random_delay:
            await asyncio.sleep(random.randint(0, self.config.random_delay) / 1000)
        return await self._wrap_retry(client, request)

    async def _wrap_retry(self, client: ClientCallable, request: Request):
        """
        Wraps the request in a retry mechanism.

        :param client: The client to use for the request.
        :param request: The request object.
        :return: The response object.
        """

        def before_sleep_log(logger):
            def _before_sleep_log(retry_state: RetryCallState):
                logger.debug(
                    f"Retrying request {request.url}, attempt {retry_state.attempt_number}",
                )

            return _before_sleep_log

        def after_log(logger):
            def _after_log(retry_state: RetryCallState):
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
            retry=retry_if_exception_type(RetryableException),
            before_sleep=before_sleep_log(logger),
            after=after_log(logger),
        )
        return await retryer(self._make_request, client, request)

    async def _make_request(self, client, request) -> Response:
        """
        Wraps client call.

        :param client: The client to use for the request.
        :param request: The request object.
        :return: The response object.
        """
        if self.config.cache.use:
            cached = await cache_request(cast(AsyncJsonCache, self.cache))
            return await cached(client, request)
        return await client(request)

    async def _iter_callbacks(
        self, callback: Generator | AsyncGenerator | Request | dict | BaseModel
    ) -> AsyncGenerator[asyncio.Task, None]:
        """
        Iterates over callbacks and creates tasks for them.

        :param callback: Either a callback iterator or a single result
        :return: An async generator of tasks.
        """
        if isinstance(callback, Generator):
            for item in callback:
                yield asyncio.create_task(self._handle_queue_item(item))
        elif isinstance(callback, AsyncGenerator):
            async for item in callback:
                yield asyncio.create_task(self._handle_queue_item(item))
        elif isinstance(callback, (Request, dict, BaseModel)):
            yield asyncio.create_task(self._handle_queue_item(callback))
        else:
            raise ValueError(f"Unknown item type {type(callback)}")

    async def fetch(self) -> None:
        """
        Fetches data items by processing the work queue.
        """
        semaphore = asyncio.Semaphore(self.config.max_concurrency)
        async with semaphore:
            if not self._started:
                await self._enqueue_start_requests()
            async with self.cache_context as cache:
                while self.has_jobs():
                    logger.debug(f"Work queue size: {self._work_queue.qsize()}")
                    item = self._work_queue.get_nowait()
                    tasks = [task async for task in self._iter_callbacks(item)]
                    await asyncio.gather(*tasks)
                    if self.config.cache.use:
                        await cache.write_periodically(self.config.cache.write_interval)

    def has_no_more_data(self) -> bool:
        """
        Check if there are no more data items in the data queue.

        :return: True if there are no more data items, False otherwise.
        """
        return self._data_queue.empty()

    def has_jobs(self) -> bool:
        """
        Check if there are jobs in the work queue.

        :return: True if there are jobs in the work queue, False otherwise.
        """
        return not self._work_queue.empty()

    def get_failures(self) -> dict[str, FailedRequest]:
        """
        Return a tuple of failed requests.

        :return: A tuple of failed requests.
        """
        return self._failures
