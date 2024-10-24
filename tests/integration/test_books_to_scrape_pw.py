from urllib.parse import urljoin

import pytest

from dataservice.clients import PlaywrightClient
from dataservice.models import Request, Response
from dataservice.service import DataService


@pytest.fixture
def client():
    return PlaywrightClient()


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


@pytest.mark.skip(
    reason="When running test_pw_intercept.py, this test is skipped, otherwise test_pw_intercept.py will fail. Needs to be investigated."
)
def test_scrape_books(data_service):
    data = tuple(data_service)
    assert len(data) == 20
