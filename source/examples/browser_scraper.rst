Browser Scraper
============

The previous examples showed how to scrape websites using `HttpXClient` to fetch HTML content.
Sometimes a simple HTTP client is not enough to scrape a website, as some websites require JavaScript to render the content,
which means that you need a browser to scrape them.

For this purpose, `DataService` provides a `PlaywrightClient` that uses the `Playwright <https://playwright.dev/python/>`_ library.
For standard HTML scraping, you can use PlaywrightClient exactly like `HttpXClient`, i.e you create an instance of `PlaywrightClient`,
pass it to the `Request` object, and then parse the HTML content in the callback function.


.. code-block:: python

    from dataservice import DataService, PlaywrightClient, Request, Response

    def parse_books_page(response: Response):
        articles = response.html.find_all("article", {"class": "product_pod"})
        return {
            "url": response.url,
            "title": response.html.title.get_text(strip=True),
            "articles": len(articles),
        }

    start_requests = [Request(url="https://books.toscrape.com/index.html", callback=parse_books_page, client=PlaywrightClient())]
    data_service = DataService(start_requests)
    data = tuple(data_service)



However, as well as fetching HTML content, `PlaywrightClient` provides additional functionality to intercept the requests that a Web page makes,
and, provided the request is a JSON or request, it can return the response in the `data` attribute of the `Response` object.

In order to intercept the requests, you need to initialize the `PlaywrightClient` with two additional parameters: `actions` and `intercept_url`.

`actions` is a coroutine function that takes a `page` argument and defines actions that you want to perform before the page is loaded.
For example, you can click on a button, type in a text field, etc.

.. code-block:: python

    from playwright.async_api import Page
    async def actions(page):
        await page.click("button")
        await page.type("input", "text")


Please note that the `actions` coroutine is not strictly necessary to intercept requests, it may also
be needed to fetch simple HTML content.

.. toctree::
   :maxdepth: 3
   :caption: Contents:

   http_scraper/initial
   http_scraper/improved
