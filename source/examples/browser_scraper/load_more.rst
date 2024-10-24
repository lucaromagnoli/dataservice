Load More
=========

This example demonstrates how to scrape a website that uses a "load more" button to load additional content.

The page that we will scrape is `DataServiceTestPage - Load More <https://lucaromagnoli.github.io/ds-mock-spa/#/load-more>`_.

The setup is similar to the previous example, but with a different `actions` coroutine function.

.. code-block:: python

    client = PlaywrightClient(actions=press_button, intercept_url="posts")


The `actions` coroutine function `press_button` is defined as follows:

.. code-block:: python

    async def press_button(page: PlaywrightPage):
        has_posts = True
        while has_posts:
            await page.get_by_role("button").click()
            await page.wait_for_timeout(1000)
            no_more_posts = page.get_by_text("No more posts")
            if await no_more_posts.is_visible():
                has_posts = False


The `press_button` function will click the "Load More" button until the "No more posts" message is displayed.

Finally, the `parse` callback is simply iterating over the response data and yielding the items.

Full code for the load more button example:

.. literalinclude:: ../../../examples/scraper/interceptor_button.py
