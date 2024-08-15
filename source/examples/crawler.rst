Books Crawler
============

In this example we will build a Crawler that follows all the page links on `Books to Scrape <https://books.toscrape.com/index.html>`_.

Building a crawler in DataService is fairly trivial.
We just need to define a function that finds all links on the page, yields them and then calls itself recursively on each link.
DataService already implements a deduplication mechanism so you don't need to worry about making unnecessary requests.
You can access the deduplication config via ``ServiceConfig``.

By default, it uses the following ``Request`` attributes to determine if a request is unique:

* ``url``

* ``params``

* ``method``

* ``form_data``

* ``json_data``

* ``content_type``

* ``headers``


First we define a simple DataItem ``Link`` that will hold the link details.

.. literalinclude:: ../../examples/scraper/crawler.py
   :pyobject: Link


The we proceed by defining the ``parse_links`` function that will extract all links from the page and yield a new ``Request`` object for each link.

.. literalinclude:: ../../examples/scraper/crawler.py
   :pyobject: parse_links
