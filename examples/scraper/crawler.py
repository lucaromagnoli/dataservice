"""Simple example of scraping books from a website with pagination argument."""

import logging
from urllib.parse import urljoin, urlparse

from dataservice import (
    BaseDataItem,
    DataService,
    HttpXClient,
    Request,
    Response,
    ServiceConfig,
    setup_logging,
)

logger = logging.getLogger("books_crawler")
setup_logging("books_crawler")


class Link(BaseDataItem):
    source: str
    destination: str
    text: str


def is_same_domain(this_url: str, that_url: str) -> bool:
    """Check if two URLs are on the same domain."""
    these_parts, those_parts = urlparse(this_url), urlparse(that_url)
    if any(not parts.netloc for parts in (these_parts, those_parts)):
        return True
    return these_parts.netloc == those_parts.netloc


def parse_links(response: Response):
    """Find all links on the page"""
    base_url = response.request.url

    links = response.html.find_all("a")
    for link in links:
        if is_same_domain(base_url, link["href"]):
            link_href = urljoin(base_url, link["href"])
            yield Link(
                source=base_url, destination=link_href, text=link.get_text(strip=True)
            )
            yield Request(
                url=link_href, callback=parse_links, client=response.request.client
            )


def main():
    client = HttpXClient()
    start_requests = iter(
        [
            Request(
                url="https://books.toscrape.com/index.html",
                callback=parse_links,
                client=client,
            )
        ]
    )
    data_service = DataService(
        start_requests, config=ServiceConfig(cache={"use": True})
    )
    data = tuple(data_service)
    for item in data:
        logger.info(item)
    for k, v in data_service.failures.items():
        logger.error(f"Error for URL: {k} - {v}")


if __name__ == "__main__":
    main()
