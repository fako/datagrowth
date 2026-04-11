Datagrowth configurations
-------------------------

Apart from creating your own configuration objects or using configuration fields,
it is also possible to leverage the ``DATAGROWTH_CONFIGURATION`` singleton.

The singleton lives in ``datagrowth.configuration`` and gives read access to the active
Datagrowth configuration values.

::

    from pathlib import Path

    from datagrowth.configuration import DATAGROWTH_CONFIGURATION

    data_dir = DATAGROWTH_CONFIGURATION.DATA_DIR
    if data_dir:
        for path in Path(data_dir).iterdir():
            print(path.name)

When a key does not exist, attribute access raises ``ConfigurationNotFoundError``.
Use ``get`` with a default value when you need a fallback:

::

    timeout = DATAGROWTH_CONFIGURATION.get("HTTP_RESOURCE_TIMEOUT", 30)

The package defaults are defined in `datagrowth.yml <https://github.com/fako/datagrowth/blob/master/datagrowth/datagrowth.yml>`_.
Use that file as the reference for available keys and default values.


Custom defaults
---------------

You can override package defaults by adding a ``datagrowth.yml`` file in your project root.
Datagrowth loads and merges this file over the package defaults.
The "global" namespace is the default and can be omitted when accessing a configuration.

Use nested namespaces in YAML that map to flat keys:

::

    global:
      data_dir: "/var/lib/datagrowth"
    shell_resource:
      bin_dir: "/usr/local/bin"

This example can be accessed as ``DATAGROWTH_CONFIGURATION.DATA_DIR`` and
``DATAGROWTH_CONFIGURATION.SHELL_RESOURCE_BIN_DIR``.

You can also override values from Django settings using ``DATAGROWTH_`` variables.
The naming convention is:

- ``DATAGROWTH_<NAMESPACE>_<KEY>`` for namespaced values (for example ``DATAGROWTH_SHELL_RESOURCE_BIN_DIR``)
- ``DATAGROWTH_<KEY>`` for global values (for example ``DATAGROWTH_DATA_DIR``)
