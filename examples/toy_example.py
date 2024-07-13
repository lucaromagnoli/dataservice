# Create a custom logger
import logging
import uuid

from dataservice.models import Request, Response
from dataservice.service import DataService
from tests.clients import ToyClient

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Create handlers
c_handler = logging.StreamHandler()
# # c_handler.setLevel(logging.INFO)
c_format = logging.Formatter("%(name)s :: %(levelname)s :: %(message)s")
c_handler.setFormatter(c_format)
logger.addHandler(c_handler)


def parse_items(response: Response):
    """Mock function that parses a list of items from a response and makes a request for each item"""
    for i in range(1, 6):
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
        yield Request(url, parse_items)


if __name__ == "__main__":
    client = ToyClient(random_sleep=1000)
    service = DataService((client,))
    service(start_requests())
