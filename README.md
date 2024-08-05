# DataService

### Lightweight, async, data gathering for Python.
#### Based on asyncio, HttpX, and BeautifulSoup.

DataService is a lightweight data gathering library for Python. Internally it uses asyncio to achieve concurrency, but it is designed to be used in a totally synchronous way.

The API is really minimal. You only need to create an instance of the `DataService` class by passing it an iterable of `Request` objects and voila', you have an iterator of data objects.
You can then iterate over this iterator, turn it into a list, a tuple, or any other data structure you want.

### Example

```python
start_requests = [Request(url="https://books.toscrape.com/index.html", callback=parse_books_page, client=HttpXClient())]
data_service = DataService(start_requests)
data = tuple(data_service)
```

A `Request` is an object that holds, among other parameters, the URL to fetch, a `client` to make the request with
and a `callback` function to parse the `Response` object.

The `client` can be any Python callable that takes a `Request` object and returns a `Response` object.
The `callback` function can be any Python callable that takes a `Response` object and returns either data or more `Request` objects.

Let's have a look at the `parse_books_page` function from the example above:

```python
def parse_books_page(response: Response):
    articles = response.soup.find_all("article", {"class": "product_pod"})
    return {
        "url": response.request.url,
        "title": response.soup.title.get_text(strip=True),
        "articles": len(articles),
    }
```
This function takes one single argument, a `Response` object. The `Response` object has a `soup` attribute that is a `BeautifulSoup` object of the HTML content of the response.
In this example we are doing some really uninspired parsing of the HTML content, but you can do whatever you want with it.
The callback function can then either `return` or `yield` either data (`dict` or `datataclass`) or more `Request` objects.

If you have used Scrapy before, you will find this pattern very familiar.

### How it works
The `DataService` class is a thin wrapper around the `DataWorker` class.
The `DataWorker` iterates over the callback chain asynchronously and handles the requests and responses data flow from the `work_queue` and stores the results in the `data_queue`.
The results are then consumed by the `DataService` class and returned to the user as a sync iterator.
