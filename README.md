# DataService

### Lightweight, async, data gathering for Python.
#### Based on asyncio, HttpX, and BeautifulSoup.

DataService is a lightweight data gathering library for Python. It uses asyncio for concurrency but is designed to be used synchronously.

The API is minimal. Create a `DataService` instance with an iterable of `Request` objects, and you get an iterator of data objects.
### Example

```python
start_requests = [Request(url="https://books.toscrape.com/index.html", callback=parse_books_page, client=HttpXClient())]
data_service = DataService(start_requests)
data = tuple(data_service)
```

A `Request` is a Pydantic model that holds the URL to fetch, a reference to the `client` callable, and a `callback` function to parse the `Response` object.

The `client` can be any Python callable that takes a `Request` object and returns a `Response` object. DataService includes a `HttpXClient` class based on the `httpx` library, but you can use any async client.

The `callback` function takes a `Response` object and returns either data or more `Request` objects.

Example `parse_books_page` function:


```python
def parse_books_page(response: Response):
    articles = response.soup.find_all("article", {"class": "product_pod"})
    return {
        "url": response.request.url,
        "title": response.soup.title.get_text(strip=True),
        "articles": len(articles),
    }
```
This function takes a `Response` object, which has a `soup` attribute (a `BeautifulSoup` object of the HTML content). The function parses the HTML content and returns data.

The callback function can return or yield either data (`dict` or `dataclass`) or more `Request` objects.

If you have used Scrapy before, you will find this pattern familiar.

### How it works under the hood
The `DataService` class is a thin wrapper around the `DataWorker` class.
The `DataWorker` iterates over the callback chain asynchronously and handles the requests and responses data flow from the `work_queue` and stores the results in the `data_queue`.
The results are then consumed by the `DataService` class and returned to the user as a sync iterator.
