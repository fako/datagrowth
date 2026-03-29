from typing import List

from django.db.transaction import atomic
from celery import current_app as app

from datagrowth.utils.tasks import DatabaseConnectionResetTask
from datagrowth.datatypes import DataStorages


@app.task(name="collection_task", base=DatabaseConnectionResetTask)
@atomic()
def collection_task(label: str, collection_ids: List[int]):
    storages = DataStorages.from_label(label)
    for collection in storages.Collection.objects.filter(id__in=collection_ids).select_for_update():
        collection.derivatives["collection_task"] = {"test": "test"}
        collection.task_results["collection_task"] = {"success": True}
        collection.save()


@app.task(name="dataset_version_task", base=DatabaseConnectionResetTask)
@atomic()
def dataset_version_task(label: str, dataset_version_ids: List[int]):
    storages = DataStorages.from_label(label)
    for version in storages.DatasetVersion.objects.filter(id__in=dataset_version_ids).select_for_update():
        version.derivatives["dataset_version_task"] = {"test": "test"}
        version.task_results["dataset_version_task"] = {"success": True}
        version.save()
