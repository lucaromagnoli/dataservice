"""Simple example of scraping books from a website with pagination argument."""

import argparse
import json
import logging
import timeit
from datetime import datetime
from functools import partial
from urllib.parse import urljoin

from dataservice import DataService, HttpXClient, Pipeline, Request, Response
from examples.logging_config import setup_logging

logger = logging.getLogger("books_scraper")
setup_logging()


def parse_books_page(response: Response, pagination: bool = True):
    articles = response.soup.find_all("article", {"class": "product_pod"})
    yield {
        "url": response.request.url,
        "title": response.soup.title.get_text(strip=True),
        "articles": len(articles),
    }
    for article in articles:
        href = article.h3.a["href"]
        url = urljoin(response.request.url, href)
        yield Request(url=url, callback=parse_book_details, client=HttpXClient())
    if pagination:
        yield from parse_pagination(response)


def parse_pagination(response):
    next_page = response.soup.find("li", {"class": "next"})
    if next_page is not None:
        next_page_url = urljoin(response.request.url, next_page.a["href"])
        yield Request(
            url=next_page_url, callback=parse_books_page, client=HttpXClient()
        )


def parse_book_details(response: Response):
    title = response.soup.find("h1").text
    price = response.soup.find("p", {"class": "price_color"}).text
    return {"title": title, "price": price}


def add_time_stamp(results: list[dict]):
    for result in results:
        result["timestamp"] = datetime.now().isoformat()
    return results


def write_to_file(results: list[dict], group_name: str = ""):
    with open(f"books{group_name}.json", "w") as f:
        json.dump(results, f, indent=4)
    logger.info("Results written to books.json")


def main(pagination: bool = True):
    start_requests = [
        Request(
            url="https://books.toscrape.com/index.html",
            callback=partial(parse_books_page, pagination=pagination),
            client=HttpXClient(),
        )
    ]

    data_service = DataService(start_requests)
    pipeline = (
        Pipeline(data_service)
        .add_step(add_time_stamp)
        .add_final_step(
            [
                partial(write_to_file),
            ]
        )
    )
    books = pipeline.run()
    for book in books:
        logger.info(book)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape books from a website.")
    parser.add_argument(
        "--pagination",
        action="store_true",
        help="Enable pagination.",
        default=False,
    )

    args = parser.parse_args()
    # main(args.workers, args.pagination)
    tt = timeit.timeit(lambda: main(False), number=1)
