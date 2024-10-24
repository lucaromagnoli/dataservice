import pytest

from dataservice.clients import PlaywrightClient
from dataservice.models import Request
from dataservice.service import DataService


def parse_intercepted(response):
    for url in response.data:
        for item in response.data[url]:
            yield {"url": url, **item}


@pytest.fixture
def client():
    return PlaywrightClient(intercept_url="/posts")


@pytest.fixture
def start_requests(client):
    return [
        Request(
            url="https://lucaromagnoli.github.io/ds-mock-spa/#/infinite-scroll",
            callback=parse_intercepted,
            client=client,
        )
    ]


@pytest.fixture
def data_service(start_requests):
    return DataService(requests=start_requests)


def test_intercept(data_service):
    data = tuple(data_service)
    assert len(data) == 10
