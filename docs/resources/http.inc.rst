
Http Resource
-------------

The ``HttpResource`` retrieves data from any HTTP source. Typically these sources are API's or websites.


Basic usage
***********

In most cases it is sufficient to declare how you want a ``HttpResource`` to fetch data.
There are a few class attributes that you need to specify to make that work::

    from datagrowth.resources import HttpResource


    class MyHTTPDataSource(HttpResource):

        URI_TEMPLATE = "https://example.com?query={}"


    data_source = MyHTTPDataSource()
    # The call below will make a request to https://example.com?query=my-query-terms
    data_source.get("my-query-terms")
    print(data_source.request)  # outputs the request being made

The ``URI_TEMPLATE`` is the most basic way to declare how resources should be fetched.
However most resources need more configuration.
This is an example using ``post``, but most attributes work for ``get`` and ``post``::

    from datagrowth.resources import HttpResource


    class MyHTTPDataSource(HttpResource):

        URI_TEMPLATE = "https://example.com"

        # Add query parameters to the end of URL's with PARAMETERS
        PARAMETERS = {
            "defaults": 1
        }

        # Or add headers with HEADERS
        HEADERS = {
            "Content-Type": "application/json"
        }

        # As this resource will now be using POST we'll add default data with DATA
        DATA = {
            "default_data": 1
        }

    data_source = MyHTTPDataSource()
    # The call below makes a POST request to https://example.com?defaults=1
    # It will add a JSON content header
    # and sends a dictionary with data containing the default_data and more_data keys.
    data_source.post(more_data="Yassss")
    print(data_source.request)  # outputs the request being made

If you need more control over parameters, headers or data,
then you can override the ``parameters``, ``headers`` and ``data`` methods.
These methods by default return the ``PARAMETERS``, ``HEADERS`` and ``DATA`` attributes.
The ``data`` method will also merge in any keyword arguments coming from the call to ``post`` if applicable.
