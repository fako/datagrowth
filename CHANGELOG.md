CHANGELOG
=========

We try to be backwards compatible as much as we can,
but this file keeps track of breaking changes in the Datagrowth package.

Under each version number you'll find a section,
which indicates breakages that you may expect when upgrading from lower versions.


v0.20
-----

This update is the first Datagrowth version that includes the ``DatasetVersion`` model.
The implementation of that model can be a steep change over current implementation.
However it's not required to implement Datagrowth's ``DatasetVersion`` to update to v0.20.
Instead you can run your own ``DatasetVersion`` which should implement ``influence`` or set the
``dataset_version`` attribute to None for ``Collection`` and ``Document``
if you don't want to use any ``DatasetVersion``.

* Adds support for Python 3.13 and removes support for 3.8.
* Removes support for Django 3.2 and adds support for Django 5.2.
* Minimal version for Celery is now 5.x.
* Minimal version for jsonschema is now 4.20.0, but jsonschema draft version remains 4.
* ``global_pipeline_app_label`` and ``global_pipeline_models`` configurations have been renamed
  to ``global_datatypes_app_label`` and ``global_datatype_models``.
* The ``extractor``, ``depends_on``, ``to_property`` and ``apply_to_resource`` configurations are now
  part of the ``growth_processor`` namespace.
* The ``batch_size`` setting is now part of the default global configuration namespace.
* The configuration ``async`` will no longer get patched to ``asynchronous`` to be compatible with Python >= 3.7.
  Instead supply ``asynchronous`` directly and replace all ``async`` occurrences.
* ``load_config`` decorator no longer excepts default values. Use ``register_defaults`` instead.
* When using ``ConfigurationType.supplement`` default values are now ignored when determining if values exist.
* The ``pipeline`` attributes gets replaced by the ``task_results`` attributes for ``Document``, ``Collection`` and
  ``DatasetVersion``.
* When writing contributions to ``Documents`` the default field is now ``derivatives``.
  Furthermore a key equal to the ``growth_phase`` is automatically added to the ``derivatives`` dictionary.
  The value for this key is always an empty dictionary. Any ``to_property`` configuration will write to this dictionary.
  Otherwise contributions get merged into the dictionary.  It's still possible to write to ``properties`` without
  adding special ``growth_phase`` keys for backward compatability.
* Contributions to ``Documents`` gathered through ``ExtractProcessor.pass_resource_through``
  may consist of simple values. If ``to_property`` is set these values will be available under that property.
  Otherwise the simple values get added to a dictionary with one "value" key and
  this dictionary gets merged like normal.
* If ``ResourceGrowthProcessor`` encounters multiple ``Resources`` per ``Document`` or
  if a single ``Resource`` yields multiple results. Then the ``reduce_contributions`` method will be called to
  determine how contribution data from ``Resources`` should compliment ``Document`` data. The default is to only use
  the first result that comes from ``Resources`` in order to be backward compatible.
* ``Resource`` class now exposes ``validate_input`` to override in child classes for input validation.
  This validation strategy will replace JSONSchema based validation for performance reasons in the future.
* Adds a ``TestClientResource`` that allows to create ``Resources`` that connect to Django views which return test data.
  Especially useful when testing Datagrowth components that take ``HttpResources`` as arguments.
* Importing ``DataStorage`` from ``datagrowth.datatypes.documents.db.base`` has to be replaced
  with importing from ``datagrowth.datatypes.storage``.
* The ``DataStorages`` dataclass has been added to manage typing for dynamically loaded ``DataStorage`` models.
* The ``DatasetVersion.task_definitions`` field holds dictionaries per ``DataStorage`` model that specifies,
  which tasks should run for which model.
* The ``DatasetVersion.errors`` field has a ``seeding`` and ``tasks`` field where some basic error information is kept
  for debugging purposes.
* A ``DatasetVersion`` will influence its ``Collections`` and ``Documents``.
  ``Collections`` may set ``DatasetVersion`` for ``Documents`` and facilitate ``DatasetVersion`` influence for them.
* Task definitions given to ``DatasetVersion`` propagate to ``Collection`` and ``Document``
  through the influence method.
* The ``Dataset.create_dataset_version`` method will create a non-pending ``DatasetVersion``
  with the default ``GROWTH_STRATEGY`` and ``DatasetVersion.tasks`` set.
  It also creates a default non-pending ``Collection`` with ``Collection.tasks`` set.
  Customize defaults by setting ``DOCUMENT_TASKS``, ``COLLECTION_TASKS``, ``DATASET_VERSION_TASKS``,
  ``COLLECTION_IDENTIFIER``, ``COLLECTION_REFEREE`` and ``DATASET_VERSION_MODEL``.
  Or override ``Dataset.get_collection_factories``, ``Dataset.get_seeding_factories`` and/or
  ``Dataset.get_task_definitions`` for more control.
* ``Document.invalidate_task`` will now always set ``pending_at`` and ``finished_at`` attributes,
  regardless of whether tasks have run before.
* The ``content`` of a Document now contains output from ``derivatives`` through ``Document.get_derivatives_content``.
* Calling ``validate_pending_data_storages`` now may update ``DatasetVersion.is_current`` and ``DatasetVersion.errors``.
* Commands inheriting from ``DatasetCommand`` that expect ``Community`` compliant objects,
  should set ``cast_as_community`` to True on the Command class and rename ``handle_dataset`` to ``handle_community``.
* Unlike the legacy ``Community`` model a ``Dataset`` has a unique signature. If the signature of a ``Dataset`` matches
  an existing ``Dataset`` the ``growth`` method will create a new ``DatasetVersion`` instead of a different ``Dataset``.
* The ``Resource`` class now specifies an abstract ``extract`` method to adhere to the strategy pattern more explicitly
and harmonize naming with ETL terminology.
* To fit better into ETL terminology ``ExtractProcessor`` now also has an alias named ``TransformProcessor``.
In the same spirit the ``extract`` method has a ``transform`` alias
and ``extract_from_resource`` a ``transform_resource`` alias.
* Using configurations with "extract" in their name remain unchanged for now,
until impact on changing them has been assessed.


v0.19
-----

* Adds support for Python 3.11, Python 3.12 and Django 4.2.
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
* The ``Collection.update``, ``Collection.add``, ``Collection.update_batches`` and ``Collection.add_batches`` will
  check for equality between ``Documents`` before adding or updating. This makes it possible to skip insert/updates in
  particular cases by overriding ``Document.__eq__``. ``Collection.add`` and ``Collection.add_batches`` require
  input as a list for this to work to prevent unexpected excessive memory usage.
* When using ``Collection.add_batches`` or ``Collection.update_batches`` a ``NO_MODIFICATION`` object can be passed
  as ``modified_at`` parameter to prevent updating ``Collection.modified_at`` with these (repeating) calls.
* The ``Collection.add_batches`` will copy ``task_results`` and ``derivatives`` fields from
  input ``Documents`` if they exist.
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
* Removes implicit Indico and Wizenoze API key loading.
* Corrects log names to "datagrowth" instead of "datascope".
* Adds a ``copy_dataset`` command that will copy a dataset by signature.
* The ``async`` configuration has been removed from settings file.
* A ``resource_exception_log_level`` setting now controls at what level ``DGResourceExceptions`` will get logged.
* Additionally ``resource_exception_reraise`` now controls whether ``DGResourceExceptions`` get reraised.
* Fallback for ``JSONField`` imports from ``django.contrib.postgres.fields`` has been removed.
* Adds ``global_allow_redirects`` configuration which controls how requests library will handle redirects.
  Defaults to True even for "head" requests.
* Exposes ``ProcessorFactory`` and ``DataStorageFactory`` to easily build processors and datatypes in the future.
* Adds the ``Collection.reload_document_ids`` method to be able to load ``Document.id`` after ``bulk_create``.
* For consistent ``Resource`` serialization adds ``serialize_resources`` and ``update_serialized_resources``.
* Experimental support for ``ResourceFixturesMixin`` that can be used to load resource content through fixture files.
* Cancelling a ``HttpFileResource`` will result in an empty body instead of a body of None.
* Removes ``load_config`` defaults parameter.
* Adds optional defaults to ``reach`` function when path can't be found in the given data structure.


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
