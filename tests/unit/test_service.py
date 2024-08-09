from __future__ import annotations

import uuid
from contextlib import nullcontext as does_not_raise

import pytest

from dataservice.data import BaseDataItem
from dataservice.models import Request, Response
from dataservice.service import DataService
from tests.unit.conftest import ToyClient


class Foo(BaseDataItem):
    """Mock data item class"""

    foo: str


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
def file_path(tmp_path):
    return tmp_path / "test.json"


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


@pytest.mark.parametrize(
    "results, expected_behaviour",
    [
        ([{"a": "a"}], does_not_raise()),
        ([Foo(foo="bar")], does_not_raise()),
    ],
)
def test_write_args_validation(file_path, results, expected_behaviour, data_service):
    with expected_behaviour:
        data_service.write(file_path, results)
