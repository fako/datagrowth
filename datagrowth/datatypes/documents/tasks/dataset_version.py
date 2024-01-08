from typing import Union, List

from celery import current_app as app

from datagrowth.exceptions import DGPendingDataStorage
from datagrowth.utils.tasks import DatabaseConnectionResetTask
from datagrowth.datatypes.types import DataStorages
from datagrowth.datatypes.documents.db.version import DatasetVersionBase
from datagrowth.datatypes.documents.tasks.base import (load_pending_data_storages, validate_pending_data_storages,
                                                       dispatch_data_storage_tasks)


@app.task(
    name="harvest_dataset_version",
    base=DatabaseConnectionResetTask,
    autoretry_for=(DGPendingDataStorage,),
    retry_kwargs={"max_retries": 5, "countdown": 5 * 60}
)
def dispatch_dataset_version_tasks(label: str, dataset_version: Union[int, DatasetVersionBase],
                                   asynchronous: bool = True, recursion_depth: int = 0,
                                   previous_tasks: List[str] = None) -> None:
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
