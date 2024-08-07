"""Simple example of scraping books from a website with pagination argument."""

import timeit
from pprint import pprint
from typing import Iterator
from urllib.parse import urljoin

from dataservice import DataService, HttpXClient, Request, Response


def parse_books_page(
    response: Response, pagination: bool = False
) -> Iterator[dict | Request]:
    articles = response.html.find_all("article", {"class": "product_pod"})
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


def parse_book_details(response: Response) -> dict:
    title = response.html.find("h1").text
    price = response.html.find("p", {"class": "price_color"}).text
    return {"title": title, "price": price}


def main():
    start_requests = [
        Request(
            url="https://books.toscrape.com/index.html",
            callback=parse_books_page,
            client=HttpXClient(),
        )
    ]

    data_service = DataService(start_requests)
    data = tuple(data_service)
    pprint(data)


if __name__ == "__main__":
    elapsed = timeit.timeit(lambda: main(), number=1)
    print(f"Elapsed time: {elapsed:.2f} seconds.")
