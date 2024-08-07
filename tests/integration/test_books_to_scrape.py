from urllib.parse import urljoin

import pytest

from dataservice.clients import HttpXClient
from dataservice.models import Request, Response
from dataservice.service import DataService


@pytest.fixture
def client():
    return HttpXClient()


def start_requests():
    urls = [
        "https://books.toscrape.com/index.html",
    ]
    for url in urls:
        yield Request(url=url, callback=parse_books, client=HttpXClient())


@pytest.fixture
def data_service(client):
    return DataService(requests=start_requests())


def parse_books(response: Response):
    articles = response.html.find_all("article", {"class": "product_pod"})
    for article in articles:
        href = article.h3.a["href"]
        url = urljoin(response.request.url, href)
        yield Request(url=url, callback=parse_book_details, client=HttpXClient())


def parse_book_details(response: Response):
    title = response.html.find("h1").text
    price = response.html.find("p", {"class": "price_color"}).text
    return {"title": title, "price": price}


def test_scrape_books(data_service):
    data = tuple(data_service)
    assert len(data) == 20
