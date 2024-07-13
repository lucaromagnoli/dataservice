import asyncio
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from logging import getLogger
from typing import Callable, Generator, Iterable, Type, Any, Optional

from dataservice.client import Client
from dataservice.models import Request, Response
from dataservice.utils import async_to_sync

MAX_ASYNC_TASKS = 10

logger = getLogger(__name__)


class SchedulerMixin:
    """Scheduler Mixin class that provides common methods for the RequestWorker and ResponseWorker classes."""

    @staticmethod
    def _enqueue_items(
        items: Iterable[Request | Response], items_queue: multiprocessing.Queue
    ):
        """Add items iterable to `items_queue`."""
        for message in items:
            logger.debug(f"Enqueueing {message.__class__.__name__.lower()} {message}")
            items_queue.put(message)

    @staticmethod
    def _items_from_queue(items_queue: multiprocessing.Queue):
        """Add items iterable to `items_queue`."""
        while not items_queue.empty():
            yield items_queue.get()

    def _enqueue_requests(
        self,
        requests_iterable: Iterable[Request],
        requests_queue: multiprocessing.Queue,
    ):
        """Add `Request` iterable to `requests_queue`."""
        self._enqueue_items(requests_iterable, requests_queue)

    def _enqueue_responses(
        self,
        responses_iterable: Iterable[Response],
        responses_queue: multiprocessing.Queue,
    ):
        """Add `Response` iterable to `responses_queue`."""
        self._enqueue_items(responses_iterable, responses_queue)

    @staticmethod
    def run_callables_in_pool_executor(
        callables_and_args: Iterable[tuple[Callable, Any]],
        max_workers: Optional[int] = 2,
    ):
        """Run callables in a ProcessPoolExecutor."""
        with ProcessPoolExecutor(max_workers=max_workers) as pool:
            futures = [
                pool.submit(*callable_and_args)
                for callable_and_args in callables_and_args
            ]
            for future in futures:
                future.result()  # Ensure all futures complete


class RequestWorker(SchedulerMixin):
    """Abstraction of a worker responsible for consuming Requests from the requests_queue and
    appending Responses to response_queue."""

    def __init__(self, clients: tuple[Client]):
        super().__init__()
        self.clients = {client.get_name(): client for client in clients}
        self._main_client = None

    def __call__(
        self,
        requests_queue: multiprocessing.Queue,
        responses_queue: multiprocessing.Queue,
    ):
        """Main entry point. This method is called by the DataService."""
        self._process_requests(requests_queue, responses_queue)

    def _get_main_client(self) -> Client:
        """Return the first client in the list of clients passed at init time."""
        if self._main_client is None:
            self._main_client = next(iter(self.clients.values()))
        return self._main_client

    def get_main_client(self) -> Client:
        """Return the first client in the list of clients passed at init time."""
        return self._get_main_client()

    def get_client_by_name(self, client_name: str | None = None) -> Client:
        """Return the instance of `Client` mapped to client_name."""
        if client_name in self.clients:
            return self.clients[client_name]
        if client_name is not None:
            logger.warning(
                f"No client with name {client_name} found. Falling back to main client."
            )
        return self.get_main_client()

    async def _process_requests_async(
        self,
        requests_queue: multiprocessing.Queue,
        responses_queue: multiprocessing.Queue,
    ):
        """Process requests asynchronously and add them to the responses queue."""
        tasks = []
        semaphore = asyncio.Semaphore(MAX_ASYNC_TASKS)

        while not requests_queue.empty():
            request = requests_queue.get()
            client = self.get_client_by_name(request.client)
            async with semaphore:
                tasks.append(asyncio.create_task(client.make_request(request)))
            if len(tasks) == MAX_ASYNC_TASKS:
                results = await asyncio.gather(*tasks)
                self._enqueue_responses(results, responses_queue)
                tasks.clear()
        if tasks:
            results = await asyncio.gather(*tasks)
            self._enqueue_responses(results, responses_queue)

    def _process_requests(
        self,
        requests_queue: multiprocessing.Queue,
        responses_queue: multiprocessing.Queue,
    ):
        """Sync wrapper around `__process_requests_async`."""
        return async_to_sync(
            self._process_requests_async, requests_queue, responses_queue
        )


class ResponseWorker(SchedulerMixin):
    def __call__(
        self,
        requests_queue: multiprocessing.Queue,
        responses_queue: multiprocessing.Queue,
        data_queue: multiprocessing.Queue,
    ):
        """Main entry point. This method is called by the DataService."""
        self._process_responses(requests_queue, responses_queue, data_queue)

    def _process_response(
        self,
        response: Response,
        requests_queue: multiprocessing.Queue,
        data_queue: multiprocessing.Queue,
    ):
        """Process a single response and put the result in the appropriate queue."""

        def process_item(req_or_dict: Request | dict):
            if isinstance(req_or_dict, Request):
                logger.debug(f"Putting request {req_or_dict.url} in request queue")
                requests_queue.put(req_or_dict)
            elif isinstance(req_or_dict, dict):
                logger.debug("Putting data item in data queue")
                data_queue.put(req_or_dict)
            else:
                raise ValueError(
                    f"Unknown type: {type(req_or_dict)}. Expected dict or Request."
                )

        logger.debug(f"Processing response {response.request.url}")
        callback_result = response.request.callback(response)

        if isinstance(callback_result, Generator):
            for item in callback_result:
                process_item(item)
        else:
            process_item(callback_result)

    def _process_responses(
        self,
        requests_queue: multiprocessing.Queue,
        responses_queue: multiprocessing.Queue,
        data_queue: multiprocessing.Queue,
    ):
        """Process responses from the responses_queue."""
        while not responses_queue.empty():
            response = responses_queue.get()
            callables_and_args = (
                (self._process_response, response, requests_queue, data_queue),
            )
            self.run_callables_in_pool_executor(callables_and_args)


class DataService(SchedulerMixin):
    """Data Service class that orchestrates the Request - Response data flow."""

    def __init__(
        self,
        clients: tuple[Type[Client]],
        pipeline: Optional[Callable[[list], None]] = None,
    ):
        super().__init__()
        self.request_worker = RequestWorker(clients)
        self.response_worker = ResponseWorker()
        self.pipeline = pipeline

    def __call__(self, requests_iterable: Iterable[Request]):
        """Main entry point. This method is called by the client."""
        return self._fetch(requests_iterable)

    def _request_response_flow(
        self,
        requests_queue: multiprocessing.Queue,
        responses_queue: multiprocessing.Queue,
        data_queue: multiprocessing.Queue,
        manager: multiprocessing.Manager,
    ):
        """Run the Request and Response workers in parallel."""
        callables_and_args = (
            (self.request_worker, requests_queue, responses_queue),
            (self.response_worker, requests_queue, responses_queue, data_queue),
        )
        return self.run_callables_in_pool_executor(callables_and_args)

    def _fetch(self, requests_iterable: Iterable[Request]):
        """
        The main Data Service data gathering logic. Passes initial requests iterable to client
        and starts the Request - Response data flow until there are no more Requests and Responses to process.
        """
        with multiprocessing.Manager() as mg:

            requests_queue, responses_queue, data_queue = (
                mg.Queue(),
                mg.Queue(),
                mg.Queue(),
            )
            self._enqueue_requests(requests_iterable, requests_queue)

            while not requests_queue.empty() or not responses_queue.empty():
                self._request_response_flow(
                    requests_queue, responses_queue, data_queue
                )

                logger.debug(
                    f"Queue sizes - requests: {requests_queue.qsize()}, responses: {responses_queue.qsize()}"
                )
            return self._process_data(data_queue)

    def _process_data(self, data_queue: multiprocessing.Queue):
        """Process data items from the data queue."""
        data_items = list(self._items_from_queue(data_queue))
        if self.pipeline is not None:
            return self.pipeline(data_items)
        return data_items
