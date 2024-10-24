Browser Scraper
============

The previous examples showed how to scrape websites using `HttpXClient` to fetch HTML content.
Sometimes a simple HTTP client is not enough to scrape a website, as some websites require JavaScript to render the content,
which means that you need a browser to scrape them.

For this purpose, `DataService` provides a `PlaywrightClient` that uses `Microsoft Playwright <https://playwright.dev/python/>`_ library.
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
and, provided the request is a JSON request, it can return the response in the `data` attribute of the `Response` object.

In order to intercept the requests, you need to initialize the `PlaywrightClient` with two additional parameters: `actions` and `intercept_url`.

.. code-block:: python

    client=PlaywrightClient(actions=actions, intercept_url="https://api.example.com/endpoint")

`actions` is a coroutine function that takes a `page` argument and defines actions that you want to perform before the page is loaded.
For example, you can click on a button, type in a text field, etc.

.. code-block:: python

    from DataService import PlaywrightPage

    async def actions(page: PlaywrightPage):
        await page.click("button")
        await page.type("input", "text")


Please note that the `actions` coroutine is not strictly necessary to intercept requests, it may or may not
be needed also to fetch simple HTML content.

`intercept_url` is a string that defines the URL that you want to intercept. It can be a full URL string or just a part of the URL, e.g. `"endpoint"`.

In the next example, we will scrape `DataServiceTestPage <https://lucaromagnoli.github.io/ds-mock-spa/>`_, a React SPA that I created for testing purposes - or rather - Chat GPT created for me 😬.

The page features two common use cases: A page with infinite scrolling and a page with a button that loads more content.
In both cases, the content is loaded via API requests to `jsonplaceholder.typicode.com.`

In this particular case, I already know the URL that I want to intercept, but normally you can find it by inspecting the network tab in the browser's developer tools.

Let's now look at examples of how to scrape the two pages using the request interception feature of `PlaywrightClient`.


.. toctree::
   :maxdepth: 3
   :caption: Contents:

   browser_scraper/infinite_scroll
   browser_scraper/load_more
