from __future__ import annotations

import asyncio
import datetime
import random
import uuid
from abc import ABC, abstractmethod
import multiprocessing
from multiprocessing import Process
from pprint import pprint
from typing import Iterator, Coroutine, Callable, Awaitable, AsyncIterator, Iterable, Generator
from uuid import UUID



class Client:
    async def make_request(self, request: Request) -> Response:
        print(f"Requesting URL: {request.url}")
        delay = random.randint(0, 2) / 100
        print(f"Waiting for {delay}")
        await asyncio.sleep(delay)
        print(f"Returning {request.url}")
        return Response(request, "response data")

class Request:
    def __init__(self, url: str, callback: Callable[[Response], Awaitable]):
        self.url = url
        self.callback = callback

class Response:
    def __init__(self, request: Request, data: [str|dict]):
        self.request = request
        self.data = data


def parse_items(response: Response):
    """Mock function that parses a list of items from a response and makes a request for each item"""
    for i in range(1, 6):
        url = f"{response.request.url}/item_{i}"
        yield Request(url, parse_item)


def parse_item(response: Response):
    """Mock function that returns a data item from the response"""
    return {"url": response.request.url, "item_id": uuid.uuid4()}


def start_requests():
    urls = [
        "http://www.idontknow.com",
        "http://www.youdontknow.com",
        "http://www.hedontknow.com",
        "http://www.shedontknow.com",
        "http://www.wedontknow.com",
        "http://www.theydontknow.com",
    ]
    for url in urls:
        yield Request(url, parse_items)


def enqueue_requests(requests_queue: multiprocessing.Queue, requests_iter: Iterable):
    for request in requests_iter:
        requests_queue.put(request)


async def process_requests_async(client, requests_queue, responses_queue):

    tasks = []
    while not requests_queue.empty():
        request = requests_queue.get()
        tasks.append(asyncio.create_task(client.make_request(request)))
    for task in tasks:
        response = await task
        responses_queue.put(response)

def async_to_sync(coro, *args, **kwargs):
    return asyncio.run(coro(*args, **kwargs))

def process_requests(client, requests_queue, responses_queue):
    return async_to_sync(process_requests_async, client, requests_queue, responses_queue)

def process_response(response, requests_queue: multiprocessing.Queue, responses_queue: multiprocessing.Queue, data_queue: multiprocessing.Queue):
    print(f'Processing response {response.request.url}')
    parsed = response.request.callback(response)
    if isinstance(parsed, Generator):
        for item in parsed:
            if isinstance(item, Request):
                print(f"Putting request {item.url} in request queue")
                requests_queue.put(item)
            elif isinstance(item, dict):
                print("Putting data item in data queue")
                data_queue.put(item)
    else:
        if isinstance(parsed, Request):
            print(f"Putting request {parsed.url} in request queue")
            requests_queue.put(parsed)
        elif isinstance(parsed, dict):
            print(f"Putting data item {parsed} in data queue")
            data_queue.put(parsed)


def process_responses(requests_queue: multiprocessing.Queue, responses_queue: multiprocessing.Queue, data_queue: multiprocessing.Queue):
    """"""
    has_responses = True
    while has_responses:
        response = responses_queue.get()
        responses_process = Process(target=process_response, args=(response, requests_queue, responses_queue, data_queue))
        responses_process.start()
        responses_process.join()
        has_responses = not responses_queue.empty()


def main():
    client = Client()
    with multiprocessing.Manager() as mg:
        requests_queue, responses_queue, data_queue = mg.Queue(), mg.Queue(), mg.Queue()
        enqueue_requests(requests_queue, start_requests())
        has_jobs = True
        while has_jobs:
            requests_process = Process(target=process_requests, args=(client, requests_queue, responses_queue))
            responses_process = Process(target=process_responses, args=(requests_queue, responses_queue, data_queue))
            requests_process.start()
            responses_process.start()
            requests_process.join()
            responses_process.join()

            has_jobs = not requests_queue.empty() or not responses_queue.empty()
            if has_jobs:
                print(f"More Jobs. requests_queue size: {requests_queue.qsize()}, responses_queue size: {responses_queue.qsize()}")
            else:
                print(f"No more jobs requests_queue size: {requests_queue.qsize()}, responses_queue size: {responses_queue.qsize()}")

        print(f"Data queue size {data_queue.qsize()}")
        while not data_queue.empty():
            data_item = data_queue.get()
            print(f"Data item {data_item}")



if __name__ == "__main__":
    main()
