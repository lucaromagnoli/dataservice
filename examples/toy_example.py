# Create a custom logger
import logging
import uuid
import time
import random

from dataservice.models import Request, Response
from dataservice.service import DataService
from pipeline import Pipeline
from tests.clients import ToyClient

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Create handlers
c_handler = logging.StreamHandler()
# # c_handler.setLevel(logging.INFO)
c_format = logging.Formatter("%(name)s :: %(levelname)s :: %(message)s")
c_handler.setFormatter(c_format)
logger.addHandler(c_handler)


async def parse_items(response: Response):
    """Mock function that parses a list of items from a response and makes a request for each item"""
    for i in range(1, 21):
        soup = response.soup
        soup.find("home")
        url = f"{response.request.url}item_{i}"
        yield Request(url=url, callback=parse_item)


def parse_item(response: Response):
    """Mock function that returns a data item from the response"""
    return {"url": response.request.url, "item_id": uuid.uuid4()}


def start_requests():
    urls = [
        "https://www.foobar.com",
        "https://www.barbaz.com",
    ]
    for url in urls:
        yield Request(url=url, callback=parse_items)


def do_something(results, something):
    new_results = []
    for result in results:
        time.sleep(random.randint(0, 200) / 100)
        print(f"Doing {something} on result {result}")
        result[something] = True
        new_results.append(result)
    return new_results


def do_x(results):
    return do_something(results, "x")


def do_y(results):
    return do_something(results, "y")


def do_z(results):
    return do_something(results, "z")


def do_w(results):
    return do_something(results, "w")


def data_pipeline(results: list[str]):
    pipeline = Pipeline()
    (pipeline.add_node(do_x).add_node(do_y).add_nodes((do_w, do_z)))
    return pipeline(results)


if __name__ == "__main__":
    client = ToyClient(random_sleep=1000)
    service = DataService(clients=(client,))
    data = service(start_requests())
