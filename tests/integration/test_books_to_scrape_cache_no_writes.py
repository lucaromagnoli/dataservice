from typing import Iterator, MutableMapping
from urllib.parse import urljoin

import pytest

from dataservice import AsyncDataService, CacheConfig, HttpXClient, ServiceConfig
from dataservice.cache import JsonCache, PickleCache
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
def json_cache_path(shared_datadir):
    return shared_datadir / "json_c.json"


@pytest.fixture
def pickle_cache_path(shared_datadir):
    return shared_datadir / "pickle_c.pkl"


@pytest.fixture
def mock_json_cache(json_cache_path, mocker):
    c = mocker.MagicMock(spec=JsonCache)
    c.sync_flush = mocker.MagicMock()
    return c


@pytest.fixture
def mock_pickle_cache(pickle_cache_path, mocker):
    c = mocker.MagicMock(spec=PickleCache)
    c.sync_flush = mocker.MagicMock()
    return c


@pytest.mark.asyncio
@pytest.fixture
async def mock_init_json_cache(mock_json_cache, mocker):
    async def _mock_init_cache():
        await mock_json_cache.load()
        return mock_json_cache

    mocker.patch(
        "dataservice.service.CacheFactory.init_cache", side_effect=_mock_init_cache
    )


@pytest.mark.asyncio
@pytest.fixture
async def mock_init_pickle_cache(mock_pickle_cache, mocker):
    async def _mock_init_cache():
        await mock_pickle_cache.load()
        return mock_pickle_cache

    mocker.patch(
        "dataservice.service.CacheFactory.init_cache", side_effect=_mock_init_cache
    )


@pytest.fixture
def json_cache_config(json_cache_path):
    return CacheConfig(cache_type="json", path=json_cache_path, use=True)


@pytest.fixture
def pickle_cache_config(pickle_cache_path):
    return CacheConfig(cache_type="pickle", path=pickle_cache_path, use=True)


@pytest.fixture
def data_service(
    request,
    start_requests,
    json_cache_config,
    pickle_cache_config,
    mock_json_cache,
    mock_pickle_cache,
):
    if request.param == "json":
        return AsyncDataService(
            requests=start_requests,
            config=ServiceConfig(max_concurrency=1, cache=json_cache_config),
        ), mock_json_cache
    elif request.param == "pickle":
        return AsyncDataService(
            requests=start_requests,
            config=ServiceConfig(max_concurrency=1, cache=pickle_cache_config),
        ), mock_pickle_cache


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
@pytest.mark.parametrize("data_service", ["json", "pickle"], indirect=True)
async def test_scrape_books_with_cache_does_not_write_to_disk(data_service):
    data_service, mock_cache = data_service
    _ = [data async for data in data_service]
    mock_cache.sync_flush.assert_not_called()
