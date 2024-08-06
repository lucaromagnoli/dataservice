DataService
===========

Lightweight - async - data gathering for Python.
____________________________________________________________________________________
DataService is a lightweight data gathering library for Python, designed with simplicity in mind.

The internal implementation uses asyncio to achieve concurrency but its interface is designed to be used synchronously.

The API is minimal and easy to use. To start, create a DataService instance with an iterable of Request objects. This setup provides you with an iterator of data objects that you can then iterate over or convert to a list, tuple, or any other iterable.

Example
-------

.. code-block:: python

    start_requests = [Request(url="https://books.toscrape.com/index.html", callback=parse_books_page, client=HttpXClient())]
    data_service = DataService(start_requests)
    data = tuple(data_service)

A ``Request`` is a ``Pydantic`` model that includes the URL to fetch, a reference to the ``client`` callable, and a ``callback`` function for parsing the ``Response`` object.

The client can be any Python callable that accepts a ``Request`` object and returns a ``Response`` object. ``DataService`` provides an ``HttpXClient`` class, which is based on the ``httpx`` library, but you are free to use your own custom async client.

The callback function processes a ``Response`` object and returns either ``data`` or additional ``Request`` objects.

In this trivial example we are requesting the books.toscrape.com homepage and parsing the number of books on the page.

Example ``parse_books_page`` function:

.. code-block:: python

    def parse_books_page(response: Response):
        articles = response.soup.find_all("article", {"class": "product_pod"})
        return {
            "url": response.request.url,
            "title": response.soup.title.get_text(strip=True),
            "articles": len(articles),
        }

This function takes a ``Response`` object, which has a ``soup`` attribute (a ``BeautifulSoup`` object of the HTML content). The function parses the HTML content and returns data.

The callback function can ``return`` or ``yield`` either ``data`` (dict or dataclass) or more ``Request`` objects.

If you have used Scrapy before, you will find this pattern familiar.

For more detailed examples and advanced usage, check out the :ref:`examples` section.
For a complete list of modules and classes, check out the :ref:`modules` section.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   examples
   modules
