from urllib.parse import urljoin

import pytest

from dataservice.client import Httpxclient
from dataservice.models import Request, Response
from dataservice.service import DataService
import dataservice.logging_config


@pytest.fixture
def client():
    return Httpxclient()

def start_requests():
    urls = [
        "https://books.toscrape.com/index.html",
    ]
    for url in urls:
        yield Request(url=url, callback=parse_books)
@pytest.fixture
def data_service(client):
    return DataService(start_requests=start_requests(), clients=(client, ))


def parse_books(response: Response):
    articles = response.soup.find_all("article", {"class": "product_pod"})
    for article in articles:
        href = article.h3.a["href"]
        url = urljoin(response.request.url, href)
        yield Request(url=url, callback=parse_book_details)

def parse_book_details(response: Response):
    title = response.soup.find("h1").text
    price = response.soup.find("p", {"class": "price_color"}).text
    return {"title": title, "price": price}


@pytest.mark.asyncio
async def test_scrape_books(data_service):
    data = [item async for item in data_service._fetch()]
    assert len(data) == 20
