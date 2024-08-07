from __future__ import annotations

import uuid
from contextlib import nullcontext as does_not_raise
from dataclasses import dataclass

import pytest

from dataservice.models import Request, Response
from dataservice.service import DataService
from tests.unit.conftest import ToyClient


@pytest.fixture
def toy_client():
    return ToyClient(random_sleep=0)


@pytest.fixture
def start_requests():
    urls = [
        "https://www.foobar.com",
        "https://www.barbaz.com",
    ]
    return [Request(url=url, callback=parse_items, client=ToyClient()) for url in urls]


@pytest.fixture
def data_service(toy_client, start_requests):
    return DataService(requests=start_requests)


async def parse_items(response: Response):
    """Mock function that parses a list of items from a response and makes a request for each item"""
    for i in range(1, 21):
        soup = response.html
        soup.find("home")
        url = f"{response.request.url}item_{i}"
        yield Request(url=url, callback=parse_item, client=ToyClient())


def parse_item(response: Response):
    """Mock function that returns a data item from the response"""
    return {"url": response.request.url, "item_id": uuid.uuid4()}


def test_toy_service(data_service):
    data = tuple(data_service)
    assert len(data) == 40
    assert [d["url"] for d in data[:20]] == [
        f"https://www.foobar.com/item_{i}" for i in range(1, 21)
    ]
    assert [d["url"] for d in data[20:]] == [
        f"https://www.barbaz.com/item_{i}" for i in range(1, 21)
    ]


@dataclass
class Foo:
    foo: str


@pytest.mark.parametrize(
    "results, filename, expected_behaviour",
    [
        ([{"a": "a"}], "test.json", does_not_raise()),
        ([Foo(foo="bar")], "test.json", does_not_raise()),
    ],
)
def test_write_args_validation(results, filename, expected_behaviour, data_service):
    with expected_behaviour:
        data_service.write(results, filename)
