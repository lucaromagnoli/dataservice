"""Simple example of scraping books from a website with pagination argument."""

import argparse
import timeit
from dataclasses import dataclass
from pprint import pprint
from typing import Iterator
from urllib.parse import urljoin

from dataservice import (
    DataService,
    DataWrapper,
    HttpXClient,
    Request,
    Response,
    ServiceConfig,
)
from dataservice.utils import setup_logging

setup_logging()


@dataclass
class BooksPage:
    url: str
    title: str
    articles: int


@dataclass
class BookDetails:
    title: str
    price: str
    url: str


def parse_books_page(
    response: Response, pagination: bool = False
) -> Iterator[BooksPage | Request]:
    articles = response.html.find_all("article", {"class": "product_pod"})
    yield BooksPage(
        **DataWrapper(
            **{
                "url": response.request.url,
                "title": lambda: response.html.title.get_text(strip=True),
                "articles": len(articles),
            }
        )
    )
    for article in articles:
        href = article.h3.a["href"]
        url = urljoin(response.request.url, href)
        yield Request(url=url, callback=parse_book_details, client=HttpXClient())
    if pagination:
        next_page = response.html.find("li", {"class": "next"})
        if next_page is not None:
            next_page_url = urljoin(response.request.url, next_page.a["href"])
            yield Request(
                url=next_page_url,
                callback=lambda resp: parse_books_page(resp, pagination=pagination),
                client=HttpXClient(),
            )


def parse_book_details(response: Response) -> BookDetails:
    return BookDetails(
        **DataWrapper(
            **{
                "title": lambda: response.html.find("h1").text,
                "price": lambda: response.html.find("p", {"class": "price_color"}).text,
                "url": response.request.url,
            }
        )
    )


def main(pagination: bool):
    start_requests = [
        Request(
            url="https://books.toscrape.com/index.html",
            callback=lambda resp: parse_books_page(resp, pagination=pagination),
            client=HttpXClient(),
        )
    ]
    service_config = ServiceConfig(random_delay=1000)
    data_service = DataService(start_requests, service_config)
    data = tuple(data_service)
    data_service.write_to_file("books.json")
    pprint(data)


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