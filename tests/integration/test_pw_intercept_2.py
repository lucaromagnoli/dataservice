import pytest

from dataservice.clients import PlaywrightInterceptClient
from dataservice.models import Request
from dataservice.service import AsyncDataService


def parse_html(response):
    return {"url": response.url}


def parse_data(response):
    for d in response.data:
        yield d


@pytest.fixture
def client():
    return PlaywrightInterceptClient(intercept_url="/posts", callback=parse_data)


@pytest.fixture
def start_requests(client):
    return [
        Request(
            url="https://lucaromagnoli.github.io/ds-mock-spa/#/infinite-scroll",
            callback=parse_html,
            client=client,
        )
    ]


@pytest.fixture
def async_data_service(start_requests):
    return AsyncDataService(requests=start_requests)


@pytest.mark.asyncio
async def test_intercept(async_data_service):
    data = [datum async for datum in async_data_service]
    assert len(data) == 11
