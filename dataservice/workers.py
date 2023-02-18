from __future__ import annotations

import asyncio
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from logging import getLogger
from multiprocessing import Process
from typing import Callable, Generator, Iterable, Type

from dataservice.client import Client
from dataservice.messages import Request, Response
from dataservice.utils import async_to_sync


class BaseWorker:
    def __init__(self):
        self.logger = getLogger(__name__)

    def _start_process(
        self, target: Callable, args: tuple[Client | multiprocessing.Queue]
    ):
        """Call `target` with `args` and start a new process"""
        p = Process(
            target=target,
            args=args,
        )
        p.start()
        return p


class RequestsWorker(BaseWorker):
    def __init__(self, clients: tuple[Client]):
        super().__init__()
        self._clients: dict[str, Client] = self._map_clients(clients)
        self._main_client = None

    def __call__(
        self,
        requests_queue: multiprocessing.Queue,
        responses_queue: multiprocessing.Queue,
    ):
        return self._process_requests(requests_queue, responses_queue)

    def _map_clients(self, clients) -> dict[str, Client]:
        return {c.get_name(): c for c in clients}

    def _get_main_client(self):
        if self._main_client is None:
            self._main_client = next(iter(self._clients.values()))
        return self._main_client

    def _get_client(self, request: Request) -> Client:
        if request.client is not None:
            if request.client not in self._clients:
                client = self._get_main_client()
                self.logger.warning(f"No client with name {request.client} found. Fall-back to {client.get_name()}.")
            return self._clients[request.client]
        else:
            return self._get_main_client()

    async def _process_requests_async(
        self,
        requests_queue: multiprocessing.Queue,
        responses_queue: multiprocessing.Queue,
    ):
        tasks = []
        while not requests_queue.empty():
            request = requests_queue.get()
            client = self._get_client(request)
            tasks.append(asyncio.create_task(client.make_request(request)))
        for task in tasks:
            response = await task
            responses_queue.put(response)

    def _process_requests(
        self,
        requests_queue: multiprocessing.Queue,
        responses_queue: multiprocessing.Queue,
    ):
        return async_to_sync(
            self._process_requests_async, requests_queue, responses_queue
        )


class ResponsesWorker(BaseWorker):
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
        self.logger.debug(f"Processing response {response.request.url}")
        parsed = response.request.callback(response)
        if isinstance(parsed, Generator):
            for item in parsed:
                if isinstance(item, Request):
                    self.logger.debug(f"Putting request {item.url} in request queue")
                    requests_queue.put(item)
                elif isinstance(item, dict):
                    self.logger.debug("Putting data item in data queue")
                    data_queue.put(item)
                else:
                    raise ValueError(
                        f"Unknown type: {type(item)}. You should yield Data or Request."
                    )
        else:
            if isinstance(parsed, Request):
                self.logger.debug(f"Putting request {parsed.url} in request queue")
                requests_queue.put(parsed)
            elif isinstance(parsed, dict):
                self.logger.debug(f"Putting data item {parsed} in data queue")
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
            with ProcessPoolExecutor(max_workers=10) as pool:
                response = responses_queue.get(block=True)
                r = pool.submit(self._process_response, response, requests_queue, data_queue)
                r.result()
                has_responses = not responses_queue.empty()


class DataService(BaseWorker):
    def __init__(self, clients: tuple[Type[Client]]):
        super().__init__()
        self.requests_worker = RequestsWorker(clients)
        self.responses_worker = ResponsesWorker()

    def _enqueue_requests(
        self,
        requests_queue: multiprocessing.Queue,
        requests_iterable: Iterable[Request],
    ):
        for request in requests_iterable:
            self.logger.debug(f"Enqueueing request {request}")
            requests_queue.put(request)

    def _run_processes(
        self,
        requests_queue: multiprocessing.Queue,
        responses_queue: multiprocessing.Queue,
        data_queue: multiprocessing.Queue,
    ):

        with ProcessPoolExecutor(max_workers=2) as pool:
            requests_future = pool.submit(self.requests_worker, requests_queue, responses_queue)
            response_future = pool.submit(self.responses_worker, requests_queue, responses_queue, data_queue)
        requests_future.result()
        response_future.result()

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
            self._enqueue_requests(requests_queue, requests_iterable)
            has_jobs = not requests_queue.empty()
            while has_jobs:
                self._run_processes(requests_queue, responses_queue, data_queue)
                has_jobs = not requests_queue.empty() or not responses_queue.empty()
                if has_jobs:
                    self.logger.debug(
                        f"More Jobs. requests_queue size: {requests_queue.qsize()}, responses_queue size: {responses_queue.qsize()}"
                    )
                else:
                    self.logger.debug(
                        f"No more jobs. requests_queue size: {requests_queue.qsize()}, responses_queue size: {responses_queue.qsize()}"
                    )

            self.logger.debug(f"Data queue size {data_queue.qsize()}")
            while not data_queue.empty():
                data_item = data_queue.get()
                self.logger.debug(f"Data item {data_item}")
