Infinite Scroll
================

This example demonstrates how to scrape a website that uses infinite scroll to load content.

The page that we will scrape is `DataServiceTestPage - Infinite Scroll <https://lucaromagnoli.github.io/ds-mock-spa/#/infinite-scroll>`_.

The URL that we want to intercept is `https://jsonplaceholder.typicode.com/posts`.

The client setup is similar to the previous example, but with the addition of the `actions` and `intercept_url` parameters.

.. code-block:: python

   client = PlaywrightClient(actions=scroll_to_bottom, intercept_url="posts")


As previously mentioned, `actions` is a coroutine function that takes a `page` argument and defines actions that you want to perform before the page is loaded.
`intercept_url` is a string that defines the URL that you want to intercept. You can either provide the full URL or just a part of it. In this case we are simply providing
the string `posts` as the URL to intercept. In more complex scenario you may need to provide a bit more of the URL to avoid intercepting unwanted requests.

In this particular example, we want to scroll to the bottom of the page to load all the content. We can achieve this by using the `page.evaluate` method to execute JavaScript code.

.. code-block:: python

   async def scroll_to_bottom(page: PlaywrightPage):
       script_path = Path(__file__).parent / "scroll_to_bottom.js"
       with open(script_path) as f:
           script = f.read()
       await page.evaluate(script)

Instead of adding the JavaScript code directly to the `actions` coroutine, we can create a separate file `scroll_to_bottom.js` and read the content from the file.

.. literalinclude:: ../../../examples/scraper/scroll_to_bottom.js
    :language: javascript

The scroll to bottom function will fire several API calls that will be intercepted and store in the data attribute of the response object as a mapping of URL to the response data.

The `parse` callback is simply iterating over the response data and yielding the items.
Obviously you can also write your own model if you prefer and yield that instead.

.. code-block:: python

   def parse_intercepted(response: Response):
       for url in response.data:
           for item in response.data[url]:
                yield {"url": url, **item}


This is pretty much it all there is to it. Below is the full code for the example.

.. literalinclude:: ../../../examples/scraper/interceptor_scroll.py
