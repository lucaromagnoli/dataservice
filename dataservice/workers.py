from __future__ import annotations

import asyncio
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from logging import getLogger
from multiprocessing import Process
from typing import Callable, Generator, Iterable, Type, NewType, Generic, Any, Optional

from dataservice.client import Client
from dataservice.messages import Request, Response
from dataservice.utils import async_to_sync

MAX_ASYNC_TASKS = 10

logger = getLogger(__name__)


class SchedulerMixin:
    """Provide functionalities to schedule tasks"""

    @staticmethod
    def _enqueue_items(items: Iterable[Request | Response], items_queue: multiprocessing.Queue):
        """
        Add items iterable to `message_queue`
        :param items: An iterable of items of the type `Request` or `Response`
        :param items_queue: The queue where the items will be added to
        :return: None
        """
        for message in items:
            logger.debug(
                f"Enqueueing {message.__class__.__name__.lower()} {message}"
            )
            items_queue.put(message)

    def _enqueue_requests(
        self,
        requests_iterable: Iterable[Request],
        requests_queue: multiprocessing.Queue,
    ):
        """
        Add `Request` iterable to `message_queue.`
        :param requests_iterable: An iterable of `Request` objects
        :param requests_queue: The queue where the Requests will be added to.
        :return: None
        """
        self._enqueue_items(requests_iterable, requests_queue)

    def _enqueue_responses(
        self,
        responses_iterable: Iterable[Request],
        responses_queue: multiprocessing.Queue,
    ):
        """
        Add `messages` iterable to `message_queue.`
        :param responses_iterable:
        :param responses_queue:
        :return: None
        """
        self._enqueue_items(responses_iterable, responses_queue)

    @staticmethod
    async def _await_tasks(tasks: list[asyncio.Future]):
        return [await task for task in tasks]

    @staticmethod
    def run_callables_in_pool_executor(
        callables_and_args: tuple[tuple[Callable, Any]],
        max_workers: Optional[int] = None,
    ):
        futures = []
        max_workers = max_workers or len(callables_and_args)
        with ProcessPoolExecutor(max_workers=max_workers) as pool:
            for callable_and_args in callables_and_args:
                futures.append(pool.submit(*callable_and_args))
            for future in futures:
                future.result()


class RequestsWorker(SchedulerMixin):
    """Abstraction of a worker responsible for consuming Requests form the requests_queue
    and appending Responses to response_queue."""

    def __init__(self, clients: tuple[Client]):
        super().__init__()
        self.clients: dict[str, Client] = self._map_clients(clients)
        self._main_client = None

    def __call__(
        self,
        requests_queue: multiprocessing.Queue,
        responses_queue: multiprocessing.Queue,
    ):
        """Main entry point. This method is called by the Supervisor"""
        return self._process_requests(requests_queue, responses_queue)

    def _map_clients(self, clients) -> dict[str, Client]:
        """Return a dictionary of client_name/client instance key/value pairs."""
        return {c.get_name(): c for c in clients}

    def _get_main_client(self) -> Client:
        """Return the first client in the list of clients passed at init time. Private method."""
        if self._main_client is None:
            self._main_client = next(iter(self.clients.values()))
        return self._main_client

    def get_main_client(self) -> Client:
        """Return the first client in the list of clients passed at init time."""
        return self._get_main_client()

    def get_client_by_name(self, client_name: Optional[str]) -> Client:
        """
        Return the instance of `Client` mapped to client_name.
        If client_name is not a known client, fall back to main client.
        :param client_name: The client classname as a string
        :return: an instance of client_name if found, main_client otherwise.
        """
        if client_name in self.clients:
            return self.clients[client_name]
        else:
            if client_name is not None:
                logger.warning(
                    f"No client with name {client_name} found. Fall-back to {client_name}."
                )
            return self.get_main_client()

    async def _process_requests_async(
        self,
        requests_queue: multiprocessing.Queue,
        responses_queue: multiprocessing.Queue,
    ):
        """
        Process requests asynchronously and add them to the responses queue.
        :param requests_queue: The queue where requests are added to.
        :param responses_queue: The queue where responses are added to.
        :return: None
        """

        tasks = []
        has_requests = not requests_queue.empty()
        while has_requests:
            request = requests_queue.get()
            client = self.get_client_by_name(request.client)
            tasks.append(asyncio.create_task(client.make_request(request)))
            has_requests = not requests_queue.empty()
            if len(tasks) == MAX_ASYNC_TASKS:
                results = await self._await_tasks(tasks)
                self._enqueue_responses(results, responses_queue)
        results = await self._await_tasks(tasks)
        self._enqueue_responses(results, responses_queue)

    def _process_requests(
        self,
        requests_queue: multiprocessing.Queue,
        responses_queue: multiprocessing.Queue,
    ):
        """
        Sync wrapper around `_process_requests_async`.
        This is the main method called in the entry point.
        :param requests_queue: The queue where requests are added to.
        :param responses_queue: The queue where responses are added to.
        :return: None
        """
        return async_to_sync(
            self._process_requests_async, requests_queue, responses_queue
        )


class ResponsesWorker(SchedulerMixin):
    def __call__(
        self,
        requests_queue: multiprocessing.Queue,
        responses_queue: multiprocessing.Queue,
        data_queue: multiprocessing.Queue,
    ):
        return self._process_responses(requests_queue, responses_queue, data_queue)

    def _process_response(
        self,
        response: Response,
        requests_queue: multiprocessing.Queue,
        data_queue: multiprocessing.Queue,
    ):
        logger.debug(f"Processing response {response.request.url}")
        parsed = response.request.callback(response)
        if isinstance(parsed, Generator):
            for item in parsed:
                if isinstance(item, Request):
                    logger.debug(f"Putting request {item.url} in request queue")
                    requests_queue.put(item)
                elif isinstance(item, dict):
                    logger.debug("Putting data item in data queue")
                    data_queue.put(item)
                else:
                    raise ValueError(
                        f"Unknown type: {type(item)}. You should yield Data or Request."
                    )
        else:
            if isinstance(parsed, Request):
                logger.debug(f"Putting request {parsed.url} in request queue")
                requests_queue.put(parsed)
            elif isinstance(parsed, dict):
                logger.debug(f"Putting data item {parsed} in data queue")
                data_queue.put(parsed)
            else:
                raise ValueError(
                    f"Unknown type: {type(parsed)}. You should return Data or Request."
                )

    def _process_responses(
        self,
        requests_queue: multiprocessing.Queue,
        responses_queue: multiprocessing.Queue,
        data_queue: multiprocessing.Queue,
    ):
        """"""
        has_responses = True
        while has_responses:
            response = responses_queue.get(block=True)
            callables_and_args = (
                (
                    self._process_response,
                    response,
                    requests_queue,
                    data_queue,
                ),
            )
            self.run_callables_in_pool_executor(callables_and_args)
            has_responses = not responses_queue.empty()


class DataSupervisor(SchedulerMixin):
    def __init__(self, clients: tuple[Type[Client]]):
        super().__init__()
        self.requests_worker = RequestsWorker(clients)
        self.responses_worker = ResponsesWorker()

    def _run_processes(
        self,
        requests_queue: multiprocessing.Queue,
        responses_queue: multiprocessing.Queue,
        data_queue: multiprocessing.Queue,
    ):
        callables_and_args = (
            (self.requests_worker, requests_queue, responses_queue),
            (self.responses_worker, requests_queue, responses_queue, data_queue),
        )
        return self.run_callables_in_pool_executor(callables_and_args, max_workers=2)

    def fetch(self, requests_iterable: Iterable[Request]):
        """
        The main Data Service entry point. Passes initial requests iterable to client
        and start the Request - Response data flow until there are no more Requests and Responses to process.
        :param requests_iterable: an Iterable of `Request` objects
        :return: None
        """
        with multiprocessing.Manager() as mg:
            requests_queue, responses_queue, data_queue = (
                mg.Queue(),
                mg.Queue(),
                mg.Queue(),
            )
            self._enqueue_requests(requests_iterable, requests_queue)
            has_jobs = not requests_queue.empty()
            while has_jobs:
                self._run_processes(requests_queue, responses_queue, data_queue)
                has_jobs = not requests_queue.empty() or not responses_queue.empty()
                if has_jobs:
                    logger.debug(
                        f"More Jobs. requests_queue size: {requests_queue.qsize()}, "
                        f"responses_queue size: {responses_queue.qsize()}"
                    )
                else:
                    logger.debug(
                        f"No more jobs. requests_queue size: {requests_queue.qsize()}, "
                        f"responses_queue size: {responses_queue.qsize()}"
                    )

            logger.debug(f"Data queue size {data_queue.qsize()}")
            while not data_queue.empty():
                data_item = data_queue.get()
                logger.debug(f"Data item {data_item}")
