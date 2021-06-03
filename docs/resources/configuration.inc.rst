
Configuration
-------------

You can adjust how a ``Resource`` retrieves data by using some configuration options.
See the `configuration`__ section to learn more on how to set configuration defaults.
Here we'll be explaining the available configurations by setting them directly only.

.. _configuration_getting_started: ../configuration/index.html

__ configuration_getting_started_


Caching behaviour
*****************

An important aspect about ``Resource`` is that it will act as a cache if retrieving data was successful.
There are a few configuration options that modify the cache behaviour. All examples below use a namespace of "global" ::

    from example import MyResource

    # This configuration disables all cache.
    # It still stores the Resource, but it will never get used twice.
    MyResource(config={
        "purge_immediately": True
    })

    # For more fine grained control the purge_after configuration can be used
    MyResource(config={
        "purge_after": {
            "days": 30
        }
    })
    # Such a configuration will indicate to Datagrowth that the Resource
    # should not be used as cache after 30 days.
    # The value of purge_after can be any dict that gets accepted as kwargs to Python's timedelta.
    # This makes it possible to be very flexible about when a Resource
    # should not get used anymore, but it won't delete any Resources.
    # Datagrowth just doesn't use them as cache after the specified time.

    # Sometimes getting data from a Resource is very computation intensive.
    # In such cases it might be a good idea to never actually retrieve data
    # unless it is cached by a background process.
    # By using the cache_only configuration you can force a Resource
    # to only return if there is a cached result and to never start real data retrieval.
    resource = MyResource(config={
        "cache_only": True
    })
    resource.get()  # this never makes a real request


User Agent configuration
************************

This configuration is only useful for ``HttpResource`` and child classes. It uses the "global" namespace ::

    from example import MyResource

    # This configuration sets the user agent for any request made by the Resource.
    MyResource(config={
        "user_agent": "My custom crawler User Agent"
    })


Backoff Delays configuration
****************************

This configuration is only useful for ``HttpResource`` and child classes.
A ``HttpResource`` will sleep for some seconds when a 420, 429, 502, 503 or 504 HTTP error occurred.
By default these sleep intervals which give the responding server some rest last 8, 16, 32, 64 and finally 128 seconds.
After the final backoff delay interval the ``HttpResource`` will error
and give up making the request if the server never responds.
You can disable or modify this behaviour by setting the ``backoff_delays`` configuration
It uses the "global" namespace ::

    from example import MyResource

    # This configuration will let the HttpResource wait 1m and then 2m instead of the default amount of seconds.
    minutes_backoff_delay = MyResource(config={
        "backoff_delays": [60, 120]
    })

    # You can also disable the backoff delay procedure.
    no_backoff_delays = MyResource(config={
        "backoff_delays": []
    })
