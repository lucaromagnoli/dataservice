REST Client
===========

In this example we will build a REST Client that fetches data from a fictional API that we'll build ourselves.

The purpose of this tutorial is not to teach you how to build REST APIs, but to show you how to use DataService to fetch data from them, so feel free to go ahead and run the
server code below to get the API up and running.

.. literalinclude:: ../../examples/api/api_server.py

This is a simple FastAPI server that serves a list of Users using page based pagination provided by `fastapi-pagination <https://github.com/uriyyo/fastapi-pagination>`_.

You can run it by executing the following commands:

.. code-block:: bash

   $ pip install "fastapi[all]" fastapi-pagination faker

   $ fastapi dev api_server.py


We can now proceed to build the REST Client that will fetch data from the API.

First we define a simple ``User`` model that will hold the user details. We are using a simple ``pydantic.BaseModel`` instead of ``BaseDataItem`` here because we are not expecting exceptions to be raised.
Please note that the same model is used in the server code.

.. literalinclude:: ../../examples/api/models.py
   :pyobject: User

Then we define the ``parse_users`` callback that will extract the user details from the API response and yield a new ``User`` object for each user.

.. literalinclude:: ../../examples/api/api_client.py
   :pyobject: parse_users

We then proceed by defining the ``paginate`` callback which will iterate over the total number of pages and yield a new ``Request`` object for each one.

.. literalinclude:: ../../examples/api/api_client.py
   :pyobject: paginate

We are starting from page 2 because the first page is already served by the initial request.

Finally we define the ``main`` function that will create the initial ``Request`` object and run the ``DataService``.


Full code for the ``api_client`` example:

.. literalinclude:: ../../examples/api/api_client.py

A few things to note in this example:

Each Request object is created with a ``content_type`` of ``json`` to tell the ``Client`` we are expecting a JSON response.
The paginate callback is also yielding ``Request`` objects using the ``params`` argument to build the URL for each page.
Finally, our fictional API is rate limited to 10 requests per minute, so we are using a ``limiter`` from `aiolimiter <https://github.com/mjpieters/aiolimiter>`_.
