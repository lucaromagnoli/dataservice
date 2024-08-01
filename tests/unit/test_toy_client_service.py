import uuid

import pytest

from dataservice.models import Request, Response
from dataservice.service import DataService
from tests.unit.clients import ToyClient


@pytest.fixture
def toy_client():
    return ToyClient(random_sleep=0)


@pytest.fixture
def start_requests():
    urls = [
        "https://www.foobar.com",
        "https://www.barbaz.com",
    ]
    return [Request(url=url, callback=parse_items, client="ToyClient") for url in urls]



@pytest.fixture
def toy_service(toy_client, start_requests):
    return DataService(requests=start_requests, clients=(toy_client,))

async def parse_items(response: Response):
    """Mock function that parses a list of items from a response and makes a request for each item"""
    for i in range(1, 21):
        soup = response.soup
        soup.find("home")
        url = f"{response.request.url}item_{i}"
        yield Request(url=url, callback=parse_item, client="ToyClient")


def parse_item(response: Response):
    """Mock function that returns a data item from the response"""
    return {"url": response.request.url, "item_id": uuid.uuid4()}

@pytest.mark.asyncio
async def test_toy_service(toy_service):
    data = [item async for item in toy_service]
    assert len(data) == 40
    assert [d['url'] for d in data[:20]] == [f"https://www.foobar.com/item_{i}" for i in range(1, 21)]
    assert [d['url'] for d in data[20:]] == [f"https://www.barbaz.com/item_{i}" for i in range(1, 21)]
