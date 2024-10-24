Initial Version
==============

We will start by writing the

.. code-block::

    parse_books_page(response: Response)

function that will extract the book URLs from each page.

The function we saw in the introduction is merely returning the total number of books on the index page.

We will now extend it to return all the book URLs for each page.

.. literalinclude:: ../../../examples/scraper/books_scraper_initial.py
   :pyobject: parse_books_page


The function now starts by yielding a dictionary with basic page details, the page URL, title, and the number of books on the page, we we will call this ``BooksPage`` for now.
It then proceeds to extract the book URLs and yields a new ``Request`` object for each book URL.
Each new request will call the ``parse_book_details`` function, which finally returns data about each book, ie ``BookDetails``.

The function is also taking a ``bool`` keyword argument, ``pagination``, which will be used to determine if we need to follow the pagination links.
If so, we parse the next page URL and yield a new ``Request`` object for the next page which calls back ``parse_book_details`` recursively, until we reach the last page and we return.

.. literalinclude:: ../../../examples/scraper/books_scraper_initial.py
   :pyobject: parse_book_details

Now we can create the ``Request`` objects to start the scraping process and run the ``DataService`` within a ``main`` function.

.. literalinclude:: ../../../examples/scraper/books_scraper_initial.py
   :pyobject: main

Full code for the ``books_scraper`` example:

.. literalinclude:: ../../../examples/scraper/books_scraper_initial.py

If you run the script, within a few seconds (pagination is off for now!),
you will see a tuple of dictionaries with the books page and book details printed to the console.

.. code-block::

   ({'articles': 20,
   'title': 'All products | Books to Scrape - Sandbox',
   'url': 'https://books.toscrape.com/index.html'},
   {'price': '£51.77', 'title': 'A Light in the Attic'},
   {'price': '£22.65', 'title': 'The Requiem Red'},
   {'price': '£17.93',
   'title': 'The Coming Woman: A Novel Based on the Life of the Infamous '
              'Feminist, Victoria Woodhull'},
   {'price': '£20.66', 'title': "Shakespeare's Sonnets"},
   {'price': '£52.29',
     'title': "Scott Pilgrim's Precious Little Life (Scott Pilgrim #1)"},
   {'price': '£23.88', 'title': 'Olio'},
   {'price': '£13.99', 'title': 'Starving Hearts (Triangular Trade Trilogy, #1)'},
   {'price': '£47.82', 'title': 'Sharp Objects'},
   {'price': '£57.25',
   'title': 'Our Band Could Be Your Life: Scenes from the American Indie '
           'Underground, 1981-1991'},
   {'price': '£52.15', 'title': 'The Black Maria'},
   {'price': '£51.33', 'title': 'Libertarianism for Beginners'},
   {'price': '£53.74', 'title': 'Tipping the Velvet'},
   {'price': '£50.10', 'title': 'Soumission'},
   {'price': '£35.02', 'title': 'Rip it Up and Start Again'},
   {'price': '£33.34',
   'title': 'The Dirty Little Secrets of Getting Your Dream Job'},
   {'price': '£22.60',
   'title': 'The Boys in the Boat: Nine Americans and Their Epic Quest for Gold '
           'at the 1936 Berlin Olympics'},
   {'price': '£37.59',
   'title': 'Mesaerion: The Best Science Fiction Stories 1800-1849'},
   {'price': '£17.46', 'title': 'Set Me Free'},
   {'price': '£45.17', 'title': "It's Only the Himalayas"},
   {'price': '£54.23', 'title': 'Sapiens: A Brief History of Humankind'})
   Elapsed time: 1.21 seconds.


Let's move on the next stage, where we will add some general improvements to the code and introduce a few more features.
