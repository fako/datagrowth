CHANGELOG
=========

We try to be backwards compatible as much as we can,
but this file keeps track of breaking changes in the Datagrowth package.

Under each version number you'll find a section, 
which indicates breakages that you may expect when upgrading from lower versions.

v0.15.0
-------

* Renamed exceptions that are prefixed with DS to names prefixed with DG.
This migrates Datascope exceptions to Datagrowth exceptions.
Affected exceptions: ``DSNoContent``, ``DSHttpError403LimitExceeded`` and ``DSInvalidResource``
* Batchize used to be a function that returned batches and possibly a leftover batch.
 Now ibatch creates batches internally.
* Reach no longer excepts paths not starting with ``$``
* Collection serializers do not include their content by default any more. 
Add it yourself by appending to default_fields or use the collection-content endpoint.
* A ``google_cx`` config value is no longer provided by default.
It should come from the ``GOOGLE_CX`` setting in your settings file.
* The ``register_config_defaults`` alias is no longer available. Use ``register_defaults`` directly.
* The ``MOCK_CONFIGURATION`` alias is no longer available.
Omit the configuration altogether and use ``register_defaults``.
* ``ExtractProcessor`` now raises ``DGNoContent``.
* ``fetch_only`` renamed to ``cache_only``
