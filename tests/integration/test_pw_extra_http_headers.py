import json

import pytest

from dataservice.clients import PlaywrightClient
from dataservice.models import Request, Response
from dataservice.service import DataService


@pytest.fixture
def client():
    return PlaywrightClient()


@pytest.fixture
def user_agent():
    return "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36"


@pytest.fixture
def start_requests(client, user_agent):
    return [
        Request(
            url="https://httpbin.org/headers",
            callback=parse_headers,
            client=client,
            headers={"User-Agent": user_agent},
        )
    ]


@pytest.fixture
def data_service(start_requests):
    return DataService(requests=start_requests)


def parse_headers(response: Response):
    headers = json.loads(response.html.find("pre").text)
    return headers


def test_headers(data_service, user_agent):
    data = tuple(data_service)
    assert len(data) == 1
    assert data[0]["headers"]["User-Agent"] == user_agent
