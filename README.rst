DataService
===========

Lightweight - async - data gathering for Python.
____________________________________________________________________________________
DataService is a lightweight data gathering library for Python.

Designed for simplicity, it's built upon common web scraping and data gathering patterns.

No complex API to learn, just standard Python idioms.

Async implementation, sync interface.

Installation
------------

You can install DataService via pip:

.. code-block:: bash

    pip install python-dataservice

How to use DataService
----------------------

To start, create a ``DataService`` instance with an ``Iterable`` of ``Request`` objects. This setup provides you with an ``Iterator`` of data objects that you can then iterate over or convert to a ``list``, ``tuple``, a ``pd.DataFrame`` or any data structure of choice.

.. code-block:: python

    start_requests = [Request(url="https://books.toscrape.com/index.html", callback=parse_books_page, client=HttpXClient())]
    data_service = DataService(start_requests)
    data = tuple(data_service)

A ``Request`` is a ``Pydantic`` model that includes the URL to fetch, a reference to the ``client`` callable, and a ``callback`` function for parsing the ``Response`` object.

The client can be any Python callable that accepts a ``Request`` object and returns a ``Response`` object. ``DataService`` provides an ``HttpXClient`` class, which is based on the ``httpx`` library, but you are free to use your own custom async client.

The callback function processes a ``Response`` object and returns either ``data`` or additional ``Request`` objects.

In this trivial example we are requesting the `Books to Scrape <https://books.toscrape.com/index.html>`_ homepage and parsing the number of books on the page.

Example ``parse_books_page`` function:

.. code-block:: python

    def parse_books_page(response: Response):
        articles = response.html.find_all("article", {"class": "product_pod"})
        return {
            "url": response.request.url,
            "title": response.html.title.get_text(strip=True),
            "articles": len(articles),
        }

This function takes a ``Response`` object, which has a ``html`` attribute (a ``BeautifulSoup`` object of the HTML content). The function parses the HTML content and returns data.

The callback function can ``return`` or ``yield`` either ``data`` (``dict`` or ``pydantic.BaseModel``) or more ``Request`` objects.

If you have used Scrapy before, you will find this pattern familiar.

For more examples and advanced usage, check out the `examples <https://dataservice.readthedocs.io/en/latest/examples.html>`_ section.

For a detailed API reference, check out the `modules <https://dataservice.readthedocs.io/en/latest/modules.html>`_  section.
