Improved Version
==============

Previously, the scraper returned data objects as raw dictionaries. Now, we use two dataclasses, BooksPage and BooksDetails, for better structure.

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

Instead, we can use ``DataWrapper``, a special Dictionary that evaluates callables on set item access,
returns the result, or None if an exception is raised, and stores the exception in the ``exceptions`` attribute.
Keys can also be accessed as attributes. For this to work we need to wrap the calls on ``soup`` in lambda functions, or a normal function if you prefer.

Example usage:

.. code-block:: python

   wrapped_data = DataWrapper(
      **{
          "title": lambda: response.soup.find("h1").text,
          "price": lambda: response.soup.find("p", {"class": "price_color"}).text,
          "url": response.request.url
         }
      )
   wrapped_data.title  # returns the title or None if an exception was raised

You can also use the helper method ``DataWrapper.maybe()`` to wrap calls outside the context of a dictionary.
This method will return a tuple of ``value, None`` or ``None, exception``.

.. code-block:: python

   maybe_value, maybe_exception = DataWrapper.maybe(lambda: response.soup.find("h1").text)

We also want to be able to pass the pagination argument to the ``scrape_books_page()`` function.
Since the ``callback`` is a one-argument function, we can use a lambda to pass the pagination argument.

We also don't want to hammer the server with requests, so we add a delay between requests using the ``ServiceConfig``.

``DataService`` doesn't come with logging out of the box, however, it provides a utility function to set up the logging for you.
By default it sets up a logger that logs to the console with the level set to DEBUGGING.

You should now see a lot of activity on the console!

Finally, so far we haven't done anything with the results. We can use the ``DataWriter`` to write the results to a CSV file.
