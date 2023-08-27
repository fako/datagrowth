CHANGELOG
=========

We try to be backwards compatible as much as we can,
but this file keeps track of breaking changes in the Datagrowth package.

Under each version number you'll find a section,
which indicates breakages that you may expect when upgrading from lower versions.


v0.19
-----

* Adds support for Python 3.11 and Django 4.2.
* Adds preliminary support for Python 3.12.
* Doesn't specify a specific parser for BeautifulSoup when loading XML content.
  BeautifulSoup warns against using Datagrowth's previous default parser (lxml) for XML parsing as it is less reliable.
* Allows ``ExtractProcessor`` to extract data using a generator function for the "@" objective.
  This can be useful to extract from nested data structures.
* Provides a ``send_iterator`` generator that initiates and sends a ``HttpResource``
  as well as any subsequent ``HttpResources``. This generator allows you to do something with in-between results
  when fetching the data.
* Provides a ``send_serie_iterator`` generator which acts like the ``send_iterator``
  except it can perform multiple send calls.
* Provides a ``content_iterator`` generator that given a ``send_iterator`` or ``send_serie_iterator``
  will extract the content from generated ``HttpResources`` using a given objective.
  This generator will also yield in-between results as extracted content.
* Adds ``Collection.add_batches`` and ``Collection.update_batches`` which are variants on
  ``Collection.add`` and ``Collection.update`` that will return generators
  instead of adding/updating everything in-memory.
* Uses ``Collection.document_update_fields`` to determine which fields to update in ``bulk_update`` calls by Collection.
* Adds ``Document.build`` to support creating a ``Document`` from raw data.
* ``Document.update`` will now use properties as update data instead of content
when giving another ``Document`` as data argument.
* Deprecates ``Collection.init_document`` in favour of ``Collection.build_document`` for consistency in naming.
* ``Document.output_from_content`` will now return lists instead of mapping generators when giving multiple arguments.
The convenience of lists is more important here than memory footprint which will be minimal anyway.
* Makes ``Document.output_from_content`` pass along content if values are not a JSON path.
* Allows ``Document.output_from_content`` to use different starting characters for replacement JSON paths.
* ``ConfigurationField.contribute_to_class`` will first call the ``TextField.contribute_to_class``
  before setting ``ConfigurationProperty`` upon the class.
* Removes validate parameter from  ``Collection.add``, ``Collection.update`` and ``Document.update``.
* Moved ``load_session`` decorator into ``datagrowth.resources.http``.
* Moved ``get_resource_link`` function into ``datagrowth.resources.http``.
* Sets default batch size to a smaller 100 elements per batch and ``Collection.update`` now respects this default.
* Removes implicit Indico and Wizenoze API key loading
* Corrects log names to "datagrowth" instead of "datascope"


v0.18
-----

* Adds support for Python 3.10 and drops support for Python 3.6.
* Uses the html.parser instead of html5lib parser when parsing HTML pages.
* Fetches the last ``Resource`` when retrieving from cache to prevent ``MultipleObjectsReturned``
exceptions in async environments
* Allows PUT as a ``HttpResource`` send method


v0.17
-----

* It's recommended to update to Django 3.2 before using Datagrowth 0.17.
* Note that a Django migration is required to make Datagrowth 0.17 work.
* Drops support for Django 1.11.
* MySQL backends are no longer supported with Django versions below 3.2
* Schemas on ``Document`` and ``Collection`` are removed as their usage is not recommended.
Consider working schemaless when using these ``DataStorage`` derivative classes.
* As schemas are no longer available for ``DataStorage`` derivative classes all write functionality
from default ``DataStorage`` API views is removed.
* ``DataStorage`` API URL patterns now require app labels as namespaces to prevent ambiguity.
* The API version can be specified using the ``DATAGROWTH_API_VERSION`` setting.
* ``DataStorage.update`` is reintroduced because of potential performance benefits.
* ``Document.update`` no longer takes first values from iterators given to it.
* ``Collection.update`` no longer excepts a single dict or Document for updating.
It also works using lookups from ``JSONField`` instead of the inferior ``reference`` mechanic.
* ``Collection.add`` applies stricter type checking: ``dict`` and ``Document`` are no longer allowed.
* ``DataStorage.url`` now provides a generic way to build URLs for ``Collection`` and ``Document``.
These URLs will expect URL patterns to exist with names in the format:
*v<api-version>:<app-name>:<model-name>-content*.
This replaces the old formats which were less flexible:
*v1:<app-name>:collection-content* and *v1:<app-name>:document-content*.
* Usage of the ``DocumentPostgres`` and ``MysqlDocument`` is deprecated. Remove these as base classes.
* ``HttpResource`` will use ``django.contrib.postgres.fields.JSONField`` or ``django.db.models.JSONField``
for ``request`` and ``head`` fields.
* ``ShellResource`` will use ``django.contrib.postgres.fields.JSONField`` or ``django.db.models.JSONField``
for the ``command`` field.
* The resources and datatypes modules now each have an admin module to import ``AdminModels`` easily.
* ``ConfigurationProperty`` now uses a simpler constructor and allows defaults for all arguments.
* Removes the unused ``global_token`` default configuration.
* Removes the unused ``http_resource_batch_size`` default configuration.
* HTTP errors 420, 429, 502, 503 and 504 will now trigger a backoff delay.
When this happens the HttpResource will sleep for the amount of seconds
specified in the ``global_backoff_delays`` setting.
Set ``global_backoff_delays`` to an empty list to disable this behaviour.
* Allows override of ``HttpResource.uri_from_url`` and ``HttpResource.hash_from_data``
* To extract from object values you know need to set ``extract_processor_extract_from_object_values`` to True.
The default is False and will result in extraction from the object directly.
* ``ShellResource`` now implements ``interval_duration`` to allow the system to pause between runs.
Useful when the command has some sort of rate limit.
* ``ExtractProcessor`` now supports application/xml content type.


v0.16
-----

* Adding support for ``Python 3.8`` and removing support for ``Python 3.5``.
* Updating ``psycopg2-binary`` to ``2.8.4``.
* HTTP tasks no longer use ``core`` as a prefix, but ``http_resource`` instead.
* Shell tasks no longer use ``core`` as a prefix, but ``shell_resource`` instead.
* HTTP task and shell task configurations require an app label prefix for any ``Resource``.
* ``load_session`` decorator now excepts None as a session and will create a requests.Session when it does.
* The ``update`` method has been removed from the ``DataStorage`` base class
* The ``data_hash`` field may now be empty in the admin on any ``Resource`` (requires a minor migration)
* The sleep dictated by ``interval_duration`` is executed by ``HttpResource`` not the http tasks
* ``ConfigurationType`` still works with the "async" property, but migrates internally to "asynchronous"
* Modern mime types like application/vnd.api+json get processed as application/json
* You can now specify to what ``datetime`` the ``Resource.purge_after`` should get set when a ``Resource`` gets saved.
The ``dict`` specified in the ``purge_after`` configuration are kwargs to a ``timedelta`` init.
This ``timedelta`` gets added to ``datetime.now``.
This means that using ``{"days": 30}`` as ``purge_after`` will set the ``Resource.purge_after``
to 30 days into the future upon creation. The ``global_purge_after`` default configuration should be an empty ``dict``.


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
