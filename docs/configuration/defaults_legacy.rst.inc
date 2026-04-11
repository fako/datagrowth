Legacy Django settings
----------------------

Before version ``0.21.x``, Datagrowth had a different mechanism to be configured through Django settings.
To keep setting names predictable across YAML, environment variables and Django settings in new Datagrowth versions,
some legacy names were renamed to namespaced keys.

The table below shows how legacy settings (``<0.21``) map to new settings (``>=0.21``):

.. list-table::
   :header-rows: 1

   * - Legacy setting (<0.21)
     - New setting (>=0.21)
   * - ``DATAGROWTH_API_VERSION``
     - ``DATAGROWTH_WEB_API_VERSION``
   * - ``DATAGROWTH_MEDIA_ROOT``
     - ``DATAGROWTH_WEB_MEDIA_ROOT``
   * - ``DATAGROWTH_BIN_DIR``
     - ``DATAGROWTH_SHELL_RESOURCE_BIN_DIR``
   * - ``DATAGROWTH_REQUESTS_PROXIES``
     - ``DATAGROWTH_HTTP_RESOURCE_REQUESTS_PROXIES``
   * - ``DATAGROWTH_REQUESTS_VERIFY``
     - ``DATAGROWTH_HTTP_RESOURCE_REQUESTS_VERIFY``
