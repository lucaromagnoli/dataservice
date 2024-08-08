Improved Version
==============

Previously, the scraper returned data objects as raw dictionaries.
We want to give a bit more structure to our data so we will define our models ``BooksPage`` and ``BooksDetails`` using the ``BaseDataItem`` class.

.. literalinclude:: ../../../examples/stages/books_scraper_improved.py
   :pyobject: BooksPage

.. literalinclude:: ../../../examples/stages/books_scraper_improved.py
   :pyobject: BookDetails


Also, in the previous version there was no exception handling for the HTML parsing.
One common issue when using long chains of attribute access in ``BeautifulSoup`` is that the code will raise an exception if any of the attributes are missing.

.. code-block:: python

   soup.find("p", {"class": "price_color"}).text

If the p tag with class "price_color" is missing, calling the ``text`` attribute will raise an exception.

Using try-except blocks for each attribute is not elegant.

For this specific purpose, ``BaseDataItem`` implements a global model pre-validator that will run callable values and store any exception in the ``errors`` dictionary.
For this to work we need to wrap the calls on the ``html`` property within lambda functions, or a normal function if you prefer.

Example usage:

.. code-block:: python

   books_page = BooksPage.wrap(
        **{
            "url": response.request.url,
            "title": lambda: response.html.title.get_text(strip=True),
            "articles": len(articles),
        }
    )


Due to this, we set the attributes to a ``str | None`` union type for those values we anticipate might be missing.

We also want to be able to pass the pagination argument to the ``scrape_books_page()`` function.
Since the ``callback`` is a one-argument function, we can use a ``lambda`` to pass the pagination argument.

We also don't want to hammer the server with requests, so we add a delay between requests using the ``ServiceConfig`` object.

``DataService`` doesn't come with logging out of the box, however, it provides a utility function to set up the logging for you.
By default it sets up a logger with name ``dataservice`` that logs to the console with the level set to DEBUGGING.

You should now see a lot of activity on the console!

Finally, so far we haven't done anything with the results. We will now iterate over the ``DataService`` iterator and group the results by Class name, then finally
write them to a CSV file using the ``write`` method.
