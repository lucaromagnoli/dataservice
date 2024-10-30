from urllib.parse import urljoin

import pytest

from dataservice.clients import HttpXClient
from dataservice.models import Request, Response
from dataservice.service import AsyncDataService, DataService


@pytest.fixture
def client():
    return HttpXClient()


@pytest.fixture
def start_requests(client):
    return [
        Request(
            url="https://books.toscrape.com/index.html",
            callback=parse_books,
            client=client,
        )
    ]


@pytest.fixture
def data_service(start_requests):
    return DataService(requests=start_requests)


@pytest.fixture
def async_data_service(start_requests):
    return AsyncDataService(requests=start_requests)


def parse_books(response: Response):
    articles = response.html.find_all("article", {"class": "product_pod"})
    for article in articles:
        href = article.h3.a["href"]
        url = urljoin(response.request.url, href)
        yield Request(url=url, callback=parse_book_details, client=response.client)


def parse_book_details(response: Response):
    title = response.html.find("h1").text
    price = response.html.find("p", {"class": "price_color"}).text
    return {"title": title, "price": price}


def test_scrape_books(data_service):
    data = tuple(data_service)
    assert len(data) == 20


@pytest.mark.asyncio
async def test_scrape_books_async(async_data_service):
    data = [datum async for datum in async_data_service]
    assert len(data) == 20
