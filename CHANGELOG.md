CHANGELOG
=========

We try to be backwards compatible as much as we can,
but this file keeps track of breaking changes in the Datagrowth package.

Under each version number you'll find a section, 
which indicates breakages that you may expect when upgrading from lower versions.

v0.15
-----

* Renamed exceptions that are prefixed with DS to names prefixed with DG.
This migrates Datascope exceptions to Datagrowth exceptions.
Affected exceptions: ``DSNoContent``, ``DSHttpError403LimitExceeded``, ``DSHttpError400NoToken``, ``DSHttpWarning300``
and ``DSInvalidResource``.
* ``batchize`` used to be a function that returned batches and possibly a leftover batch.
 Now ``ibatch`` creates batches internally.
* ``reach`` no longer excepts paths not starting with ``$``
* Collection serializers do not include their content by default any more. 
Add it yourself by appending to default_fields or use the collection-content endpoint.
* A ``google_cx`` config value is no longer provided by default.
It should come from the ``GOOGLE_CX`` setting in your settings file.
* The ``register_config_defaults`` alias is no longer available. Use ``register_defaults`` directly.
* The ``MOCK_CONFIGURATION`` alias is no longer available.
Omit the configuration altogether and use ``register_defaults``.
* Passing a default configuration to ``load_config`` is deprecated. Use ``register_defaults`` instead.
* ``ExtractProcessor`` now raises ``DGNoContent``.
* ``fetch_only`` renamed to ``cache_only``
* Non-existing resources will now raise a ``DGResourceDoesNotExist`` if ``cache_only`` is True
* ``meta`` property is removed from ``Resource`` use ``variables`` method instead.
* All data hashes will be invalidated, because hasher now sorts keys.
* ``schema`` is allowed to be empty on ``DataStorage``, which means there will be no validation by default.
This is recommended, but requires migrations for some projects.
* ``_handle_errors`` has been renamed to ``handle_errors`` and is an explicit candidate for overriding.
* ``_update_from_response`` has been renamed to ``_update_from_results`` for more consistent Resource api.
* Dumps KaldiNL results into an output folder instead of KaldiNL root.


v0.16
-----

* Adding support for ``Python 3.8`` and removing support for ``Python 3.5``.
* Updating ``psycopg2-binary`` to ``2.8.4``.
* HTTP tasks no longer use ``core`` as a prefix, but ``http_resource`` instead.
* Shell tasks no longer use ``core`` as a prefix, but ``shell_resource`` instead.
* HTTP task and shell task configurations require an app label prefix for any ``Resource``.
* load_session decorator now excepts None as a session and will create a requests.Session.
