Improved Version
==============

Previously, the scraper returned data objects as raw dictionaries.
We want to give a bit more structure to our data so we will define our models ``BooksPage`` and ``BooksDetails`` using the ``BaseDataItem`` class.

.. literalinclude:: ../../../examples/stages/books_scraper_improved.py
   :pyobject: BooksPage

.. literalinclude:: ../../../examples/stages/books_scraper_improved.py
   :pyobject: BookDetails


Also, in the previous version there was no exception handling for the HTML parsing.
One common issue when using access chains in ``BeautifulSoup`` is that the code will raise an exception if there's a method call or property access on a missing attribute.
E.g.

.. code-block:: python

   html.find("p", {"class": "price_color"}).text

If the p tag with class "price_color" is missing, accessing the ``text`` attribute will raise an exception.

Using try-except blocks or if conditions for each attribute is not a very elegant solution.

For this specific purpose, you can use ``BaseDataItem``. A Pydantic model with a global pre-validator that will invoke callable values
and store any exception in the ``errors`` dictionary attribute.
For this to work, we need to wrap the calls on the ``html`` property within a callable.

Example usage:

.. code-block:: python

   BookDetails(
        **{
            "title": lambda: response.html.find("h1").text,
            "price": lambda: response.html.find("p", {"class": "price_color"}).text,
            "url": response.request.url,
        }
    )

Under the hood, ``BaseDataItem`` uses a ``DataWrapper`` dict. You can import it from ``dataservice`` and use it directly if you need to handle exceptions outside of the context of a ``BaseDataItem``.

.. code-block:: python

   from dataservice import DataWrapper

   wrapped = DataWrapper(
        **{
            "title": lambda: response.html.find("h1").text,
            "price": lambda: response.html.find("p", {"class": "price_color"}).text,
            "url": response.request.url,
        }
   )
   if wrapped.errors:
       print(wrapped.errors)



We don't want to hammer the server with too many concurrent requests, so we add random delay between requests using the ``ServiceConfig`` object.
``ServiceConfig`` is a simple class that allows custom configuration for your ``DataService`` object.

We also want to activate the cache in case we need to re-run the scraper. We can do this by setting the ``cache`` attribute to ``True``.
By default, a file named ``cache.json`` will be created in the current working directory. You can also specify a custom path with the ``path`` key.

.. code-block:: python

   from dataservice import ServiceConfig

   service_config = ServiceConfig(random_delay=1000, cache={"use": True})


``DataService`` doesn't come with logging on out of the box, however, it provides a utility function to set up a simple console logging for you.
By default it creates a logger with name ``dataservice`` that logs to the console with level set to DEBUG. You can also pass a custom logger name and use the same logger setup, like so.

.. code-block:: python

   from dataservice import setup_logging

   logger = getLogger("books_scraper")
   setup_logging("books_scraper")


Please note that this utility has been coded for simplicity and may not be suitable for all use cases. For more advanced logging, you should set up your own logger.

So far we haven't done anything with the results. We will now iterate over the ``DataService`` iterator and group the results by class name, then
write them to a JSON file using the ``write`` utility method. Currently the ``write`` method supports JSON and CSV formats.

Finally, we want to be able to pass the pagination argument to the ``parse_books_page()`` function. Since we know that
callbacks are one-argument functions, we will use a lambda to pass the pagination argument. You can also, of course, use a partial function if you want.

.. note::
   We previously mentioned that the Client can be any Python callable. In our code however, we are creating an instance
   of the ``HttpXClient()`` class, whose main method ``make_request()`` is invoked via magic method ``__call__``.


Full code for the improved example:

.. literalinclude:: ../../../examples/scraper/books_scraper_improved.py


If you now run the script with pagination enabled, you should see something like this:

.. code-block:: bash

   $ python books_scraper_improved.py --pagination

.. code-block::

   2024-08-15 18:38:17,557 :: dataservice.clients :: INFO :: Received response for https://books.toscrape.com/catalogue/alice-in-wonderland-alices-adventures-in-wonderland-1_5/index.html
   2024-08-15 18:38:17,634 :: dataservice.clients :: INFO :: Received response for https://books.toscrape.com/catalogue/ajin-demi-human-volume-1-ajin-demi-human-1_4/index.html
   2024-08-15 18:38:17,654 :: dataservice.cache :: DEBUG :: Cache miss for https://books.toscrape.com/catalogue/choosing-our-religion-the-spiritual-lives-of-americas-nones_14/index.html
   2024-08-15 18:38:17,654 :: dataservice.clients :: INFO :: Requesting https://books.toscrape.com/catalogue/choosing-our-religion-the-spiritual-lives-of-americas-nones_14/index.html
   2024-08-15 18:38:17,683 :: dataservice.cache :: DEBUG :: Cache miss for https://books.toscrape.com/catalogue/frankenstein_20/index.html
   2024-08-15 18:38:17,683 :: dataservice.clients :: INFO :: Requesting https://books.toscrape.com/catalogue/frankenstein_20/index.html
   2024-08-15 18:38:17,744 :: dataservice.cache :: DEBUG :: Cache miss for https://books.toscrape.com/catalogue/deep-under-walker-security-1_15/index.html
   2024-08-15 18:38:17,744 :: dataservice.clients :: INFO :: Requesting https://books.toscrape.com/catalogue/deep-under-walker-security-1_15/index.html
   2024-08-15 18:38:17,786 :: dataservice.cache :: DEBUG :: Cache miss for https://books.toscrape.com/catalogue/bleach-vol-1-strawberry-and-the-soul-reapers-bleach-1_7/index.html
   2024-08-15 18:38:17,786 :: dataservice.clients :: INFO :: Requesting https://books.toscrape.com/catalogue/bleach-vol-1-strawberry-and-the-soul-reapers-bleach-1_7/index.html
   2024-08-15 18:38:18,027 :: dataservice.clients :: INFO :: Received response for https://books.toscrape.com/catalogue/emma_17/index.html
   2024-08-15 18:38:18,171 :: dataservice.clients :: INFO :: Received response for https://books.toscrape.com/catalogue/frankenstein_20/index.html
   2024-08-15 18:38:18,208 :: dataservice.clients :: INFO :: Received response for https://books.toscrape.com/catalogue/choosing-our-religion-the-spiritual-lives-of-americas-nones_14/index.html
   2024-08-15 18:38:18,247 :: dataservice.clients :: INFO :: Received response for https://books.toscrape.com/catalogue/deep-under-walker-security-1_15/index.html
   2024-08-15 18:38:18,323 :: dataservice.clients :: INFO :: Received response for https://books.toscrape.com/catalogue/bleach-vol-1-strawberry-and-the-soul-reapers-bleach-1_7/index.html
   2024-08-15 18:38:18,335 :: dataservice.cache :: INFO :: Writing cache to cache.json
   2024-08-15 18:38:18,790 :: dataservice.files :: INFO :: Data written to books_pages.json
   2024-08-15 18:38:18,804 :: dataservice.files :: INFO :: Data written to book_details.json
   'Elapsed time: 256.19 seconds'
   2024-08-15 18:38:19,534 :: dataservice.cache :: INFO :: Writing cache to cache.json


Let's checkout how to write a crawler that can follow links to other pages.
