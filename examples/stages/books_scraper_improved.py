"""Simple example of scraping books from a website with pagination argument."""

import argparse
import timeit
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
)
from dataservice.utils import setup_logging

setup_logging()


class BooksPage(BaseDataItem):
    url: str
    title: str | None
    articles: int


class BookDetails(BaseDataItem):
    url: str
    title: str | None
    price: str | None


def parse_books_page(
    response: Response, pagination: bool = False
) -> Iterator[BooksPage | Request]:
    """Parse the books page."""
    articles = response.html.find_all("article", {"class": "product_pod"})

    yield BooksPage.wrap(
        **{
            "url": response.request.url,
            "title": lambda: response.html.title.get_text(strip=True),
            "articles": len(articles),
        }
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
    """Parse the book details."""
    return BookDetails.wrap(
        **{
            "title": lambda: response.html.find("h1").text,
            "price": lambda: response.html.find("p", {"class": "price_color"}).text,
            "url": response.request.url,
        }
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
    data = {type(item).__name__: item for item in data_service}
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
