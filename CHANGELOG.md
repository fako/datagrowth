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
