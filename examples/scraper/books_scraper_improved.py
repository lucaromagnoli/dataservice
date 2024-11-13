"""Simple example of scraping books from a website with pagination argument."""

import argparse
import timeit
from collections import defaultdict
from logging import getLogger
from pprint import pprint
from typing import Iterator
from urllib.parse import urljoin

from dataservice import (
    BaseDataItem,
    DataService,
    HttpXClient,
    Request,
    Response,
    ServiceConfig,
    setup_logging,
)

logger = getLogger("books_scraper")
setup_logging("books_scraper")


class BooksPage(BaseDataItem):
    url: str
    title: str | None
    books: int


class BookDetails(BaseDataItem):
    url: str
    title: str | None
    price: str | None


def parse_books_page(
    response: Response, pagination: bool = False
) -> Iterator[BooksPage | Request]:
    """Parse the books page."""
    articles = response.html.find_all("article", {"class": "product_pod"})

    yield BooksPage(
        **{
            "url": response.request.url,
            "title": lambda: response.html.title.get_text(strip=True),
            "books": len(articles),
        }
    )

    for article in articles:
        href = article.h3.a["href"]
        url = urljoin(response.request.url, href)
        yield Request(url=url, callback=parse_book_details, client=response.client)

    if pagination:
        next_page = response.html.find("li", {"class": "next"})
        if next_page is not None:
            next_page_url = urljoin(response.request.url, next_page.a["href"])
            yield Request(
                url=next_page_url,
                callback=lambda resp: parse_books_page(resp, pagination=pagination),
                client=response.client,
            )


def parse_book_details(response: Response) -> BookDetails:
    """Parse the book details."""
    return BookDetails(
        **{
            "title": lambda: response.html.find("h1").text,
            "price": lambda: response.html.find("p", {"class": "price_color"}).text,
            "url": response.url,
        }
    )


def main(pagination: bool):
    httpx_client = HttpXClient()
    start_requests = [
        Request(
            url="https://books.toscrape.com/index.html",
            callback=lambda resp: parse_books_page(resp, pagination=pagination),
            client=httpx_client,
        )
    ]
    service_config = ServiceConfig(delay={"amount": 10000}, cache={"use": True})
    data_service = DataService(start_requests, service_config)
    data = defaultdict(list)
    for item in data_service:
        data[type(item).__name__].append(item)
    data_service.write("books_pages.json", data["BooksPage"])
    data_service.write("book_details.json", data["BookDetails"])


if __name__ == "__main__":
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument(
        "--pagination",
        action="store_true",
        help="Enable pagination to scrape multiple pages",
    )
    args = args_parser.parse_args()
    elapsed = timeit.timeit(lambda: main(args.pagination), number=1)
    pprint("Elapsed time: {:.2f} seconds".format(elapsed))
