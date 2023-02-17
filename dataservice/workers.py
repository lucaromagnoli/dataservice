from __future__ import annotations

import asyncio
import multiprocessing
from logging import getLogger
from multiprocessing import Process
from typing import Callable, Generator, Iterable

from dataservice.client import Client
from dataservice.http import Request, Response
from dataservice.utils import async_to_sync


class BaseWorker:
    def __init__(self):
        self.logger = getLogger(__name__)

    def start_process(
        self, target: Callable, args: tuple[Client | multiprocessing.Queue]
    ):
        p = Process(
            target=target,
            args=args,
        )
        p.start()
        return p


class RequestsWorker(BaseWorker):
    def __call__(
        self,
        client: Client,
        requests_queue: multiprocessing.Queue,
        responses_queue: multiprocessing.Queue,
    ):
        return self.process_requests(client, requests_queue, responses_queue)

    async def process_requests_async(
        self,
        client: Client,
        requests_queue: multiprocessing.Queue,
        responses_queue: multiprocessing.Queue,
    ):
        tasks = []
        while not requests_queue.empty():
            request = requests_queue.get()
            tasks.append(asyncio.create_task(client.make_request(request)))
        for task in tasks:
            response = await task
            responses_queue.put(response)

    def process_requests(
        self,
        client: Client,
        requests_queue: multiprocessing.Queue,
        responses_queue: multiprocessing.Queue,
    ):
        return async_to_sync(
            self.process_requests_async, client, requests_queue, responses_queue
        )


class ResponsesWorker(BaseWorker):
    def __call__(
        self,
        requests_queue: multiprocessing.Queue,
        responses_queue: multiprocessing.Queue,
        data_queue: multiprocessing.Queue,
    ):
        return self.process_responses(requests_queue, responses_queue, data_queue)

    def process_response(
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

    def process_responses(
        self,
        requests_queue: multiprocessing.Queue,
        responses_queue: multiprocessing.Queue,
        data_queue: multiprocessing.Queue,
    ):
        """"""
        has_responses = True
        while has_responses:
            response = responses_queue.get(block=True)
            self.start_process(
                self.process_response, (response, requests_queue, data_queue)
            )
            has_responses = not responses_queue.empty()


class DataService(BaseWorker):
    def __init__(self):
        super().__init__()
        self.client = Client()
        self.requests_worker = RequestsWorker()
        self.responses_worker = ResponsesWorker()

    def enqueue_requests(
        self,
        requests_queue: multiprocessing.Queue,
        requests_iterable: Iterable[Request],
    ):
        for request in requests_iterable:
            self.logger.debug(f"Enqueueing request {request}")
            requests_queue.put(request)

    def run_processes(
        self,
        requests_queue: multiprocessing.Queue,
        responses_queue: multiprocessing.Queue,
        data_queue: multiprocessing.Queue,
    ):
        processes = (
            self.start_process(
                self.requests_worker, (self.client, requests_queue, responses_queue)
            ),
            self.start_process(
                self.responses_worker, (requests_queue, responses_queue, data_queue)
            ),
        )
        for process in processes:
            process.join()

    def fetch(self, requests_iterable: Iterable[Request]):
        with multiprocessing.Manager() as mg:
            requests_queue, responses_queue, data_queue = (
                mg.Queue(),
                mg.Queue(),
                mg.Queue(),
            )
            self.enqueue_requests(requests_queue, requests_iterable)
            has_jobs = not requests_queue.empty()
            while has_jobs:
                self.run_processes(requests_queue, responses_queue, data_queue)
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
