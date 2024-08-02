"""Simple example of scraping books from a website with pagination argument."""
import argparse
import asyncio
import logging
from functools import partial
from urllib.parse import urljoin

from clients import HttpXClient
from logging_config import setup_logging

from dataservice.models import Request, Response
from dataservice.service import DataService

logger = logging.getLogger("books_scraper")
setup_logging()


def parse_books(response: Response, pagination: bool = True):
    articles = response.soup.find_all("article", {"class": "product_pod"})
    yield {"url": response.request.url, "title": response.soup.title.text}
    for article in articles:
        href = article.h3.a["href"]
        url = urljoin(response.request.url, href)
        yield Request(url=url, callback=parse_book_details)
    if pagination:
        yield from parse_pagination(response)


def parse_pagination(response):
    next_page = response.soup.find("li", {"class": "next"})
    if next_page is not None:
        next_page_url = urljoin(response.request.url, next_page.a["href"])
        yield Request(url=next_page_url, callback=parse_books)


def parse_book_details(response: Response):
    title = response.soup.find("h1").text
    price = response.soup.find("p", {"class": "price_color"}).text
    return {"title": title, "price": price}


async def main(args):
    client = HttpXClient()
    start_requests = iter(
        [
            Request(
                url="https://books.toscrape.com/index.html",
                callback=partial(parse_books, pagination=args.pagination),
            )
        ]
    )
    data_service = DataService(start_requests, clients=(client,))
    # with Pipeline(data_service) as data_pipeline:
    #     pipeline.add(do_x)
    #     data = pipeline.run(data)
    logger.info(f"Scraped {len(data)} books.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape books from a website.")
    parser.add_argument(
        "--pagination",
        action="store_true",
        help="Enable pagination.",
        default=False,
    )
    asyncio.run(main(args=parser.parse_args()))
