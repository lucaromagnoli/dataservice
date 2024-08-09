"""Simple example of scraping books from a website with pagination argument."""

import argparse
import logging
from pprint import pprint
from urllib.parse import urljoin

from dataservice import (
    BaseDataItem,
    DataService,
    HttpXClient,
    Request,
    Response,
    setup_logging,
)

logger = logging.getLogger("books_scraper")
setup_logging()


class Link(BaseDataItem):
    source: str
    destination: str
    text: str


def get_links(response: Response):
    base_url = response.request.url

    def inner(resp: Response):
        nonlocal base_url
        links = resp.html.find_all("a")
        for link in links:
            link_href = urljoin(base_url, link["href"])
            yield Link(
                source=base_url, destination=link_href, text=link.get_text(strip=True)
            )
            yield Request(url=link_href, callback=inner, client=HttpXClient())

    yield from inner(response)


def main(args):
    start_requests = iter(
        [
            Request(
                url="https://books.toscrape.com/index.html",
                callback=get_links,
                client=HttpXClient(),
            )
        ]
    )
    data_service = DataService(start_requests)
    data = tuple(data_service)
    pprint(data)
    print(len(data))
    print(data_service.failures)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawl books from a website.")
    parser.add_argument(
        "--pagination",
        action="store_true",
        help="Enable pagination.",
        default=False,
    )
    main(args=parser.parse_args())
