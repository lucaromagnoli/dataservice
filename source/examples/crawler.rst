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


Then we proceed by defining the ``parse_links`` function that will extract all links from the page and yield a new ``Request`` object for each link.

.. literalinclude:: ../../examples/scraper/crawler.py
   :pyobject: parse_links


A few things to note in the function above:

We are generating a new ``Request`` object for each link found on the page using the initial URL as the base URL.
We are also checking if the link is relative and converting it to an absolute URL. Furthermore we are filtering out any links that are not part of the same domain to prevent the crawler from running forever.

.. literalinclude:: ../../examples/scraper/crawler.py
   :pyobject: is_same_domain

Full code for the ``crawler`` example:

.. literalinclude:: ../../examples/scraper/crawler.py

In this example, after fetching data, we will log the results to console as well as the errors that occurred during the scraping process,
by accessing the ``failures`` attribute of the ``DataService`` instance.

Let's now move on to the REST Client examples too see how we can use the ``DataService`` to fetch data from REST APIs.
