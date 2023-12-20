from typing import Union, List

from django.db.transaction import atomic
from celery import current_app as app

from datagrowth.exceptions import DGPendingDataStorage
from datagrowth.utils.tasks import DatabaseConnectionResetTask
from datagrowth.datatypes import (DataStorages, load_pending_data_storages, validate_pending_data_storages,
                                  dispatch_data_storage_tasks)
from datagrowth.datatypes.documents.db.version import DatasetVersionBase


@app.task(
    name="harvest_dataset_version",
    base=DatabaseConnectionResetTask,
    autoretry_for=(DGPendingDataStorage,),
    retry_kwargs={"max_retries": 5, "countdown": 5 * 60}
)
def dispatch_dataset_version_tasks(label: str, dataset_version: Union[int, DatasetVersionBase], asynchronous: bool = True,
                                   recursion_depth: int = 0, previous_tasks: List[str] = None) -> None:
    if recursion_depth >= 10:
        raise RecursionError("Maximum harvest_dataset_version recursion reached")
    previous_tasks = previous_tasks or []
    # Load DatasetVersion and check its state
    storages = DataStorages.load_instances(label, dataset_version)
    dataset_version = storages.instance
    if not load_pending_data_storages(dataset_version, model=storages.DatasetVersion):
        # parallel tasks may already picked-up this dispatch and nothing should be processed
        return

    # Dispatch pending tasks
    pending = validate_pending_data_storages(dataset_version, model=storages.DatasetVersion)
    pending_tasks = [task for instance in pending for task in instance.get_pending_tasks()]
    if len(pending) and pending_tasks != previous_tasks:  # we're not repeating the same tasks indefinitely
        recursive_callback_signature = dispatch_dataset_version_tasks.si(
            label,
            dataset_version.id,
            asynchronous=asynchronous,
            recursion_depth=recursion_depth+1,
            previous_tasks=pending_tasks
        )
        dispatch_data_storage_tasks(
            label,
            *pending,
            callback=recursive_callback_signature,
            asynchronous=asynchronous
        )


@app.task(name="set_current_dataset_version", base=DatabaseConnectionResetTask)
@atomic
def set_current_dataset_version(label: str, dataset_version_id: int) -> None:
    storages = DataStorages.load_instances(label, dataset_version_id, lock=True)
    dataset_version = storages.instance
    # A Collection is unfinished when it is not yet pending (because Documents are still coming in),
    # but any tasks for the Collection haven't run either
    has_unfinished_sets = dataset_version.sets.filter(finished_at__isnull=True).exists()
    # A Collection will become pending when all Documents have been fetched and stored
    # and will remain pending as long as not all tasks have been completed
    has_pending_sets = dataset_version.sets.filter(pending_at__isnull=False).exists()
    # We only want to set the DatasetVersion to become "current",
    # meaning all output will use this DatasetVersion, when all tasks for all sets have executed.
    should_set_current = not has_unfinished_sets and not has_pending_sets
    if should_set_current:
        dataset_version.set_current()
        dataset_version.pipeline["set_current_dataset_version"] = {"success": True}
        dataset_version.save()
