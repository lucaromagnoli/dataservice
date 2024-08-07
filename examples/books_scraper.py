"""Simple example of scraping books from a website with pagination argument."""

import argparse
import json
import logging
import timeit
from datetime import datetime
from functools import partial
from pprint import pprint
from urllib.parse import urljoin

from dataservice import DataService, HttpXClient, Pipeline, Request, Response
from dataservice.utils import setup_logging

logger = logging.getLogger("books_scraper")
setup_logging()


def parse_books_page(response: Response, pagination: bool = True):
    articles = response.html.find_all("article", {"class": "product_pod"})
    # BooksPage
    yield {
        "url": response.request.url,
        "title": response.html.title.get_text(strip=True),
        "articles": len(articles),
    }
    for article in articles:
        href = article.h3.a["href"]
        url = urljoin(response.request.url, href)
        yield Request(url=url, callback=parse_book_details, client=HttpXClient())
    if pagination:
        next_page = response.html.find("li", {"class": "next"})
        if next_page is not None:
            next_page_url = urljoin(response.request.url, next_page.a["href"])
            yield Request(
                url=next_page_url, callback=parse_books_page, client=HttpXClient()
            )


def parse_book_details(response: Response):
    title = response.html.find("h1").text
    price = response.html.find("p", {"class": "price_color"}).text
    # BookDetails
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
    results = tuple(data_service)
    pprint(results)
    pipeline = (
        Pipeline(results)
        .add_step(add_time_stamp)
        .add_step(partial(write_to_file), final=True)
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
    main(args.pagination)
