from typing import Iterator, MutableMapping
from urllib.parse import urljoin

import pytest

from dataservice import AsyncDataService, CacheConfig, HttpXClient, ServiceConfig
from dataservice.cache import LocalJsonCache
from dataservice.models import Request, Response


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
def cache_path(shared_datadir):
    return shared_datadir / "cache.json"


@pytest.fixture
def mock_cache(cache_path, mocker):
    c = mocker.MagicMock(spec=LocalJsonCache)
    c.sync_flush = mocker.MagicMock()
    return c


@pytest.mark.asyncio
@pytest.fixture
async def mock_init_cache(mock_cache, mocker):
    async def _mock_init_cache():
        await mock_cache.load()
        return mock_cache

    mocker.patch(
        "dataservice.service.CacheFactory.init_cache", side_effect=_mock_init_cache
    )


@pytest.fixture
def cache_config(cache_path):
    return CacheConfig(cache_type="local", path=cache_path, use=True)


@pytest.fixture
def data_service(start_requests, cache_config, mock_cache):
    return AsyncDataService(
        requests=start_requests,
        config=ServiceConfig(max_concurrency=1, cache=cache_config),
    )


def parse_books_page(
    response: Response, *, page: int = 1
) -> Iterator[MutableMapping | Request]:
    """Parse the books page."""
    articles = response.html.find_all("article", {"class": "product_pod"})
    for article in articles:
        href = article.h3.a["href"]
        url = urljoin(response.request.url, href)
        yield Request(url=url, callback=parse_book_details, client=response.client)

        next_page = response.html.find("li", {"class": "next"})
        page += 1
        if next_page is not None and page < 5:
            next_page_url = urljoin(response.request.url, next_page.a["href"])
            yield Request(
                url=next_page_url,
                callback=lambda resp: parse_books_page(resp, page=page),
                client=response.client,
            )


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


@pytest.mark.asyncio
async def test_scrape_books_with_cache_does_not_write_to_disk(
    data_service, mock_cache, mock_init_cache
):
    _ = [data async for data in data_service]
    mock_cache.sync_flush.assert_not_called()
