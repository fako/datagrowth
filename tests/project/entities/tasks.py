from typing import List

from django.db.transaction import atomic
from celery import current_app as app

from datagrowth.utils.tasks import DatabaseConnectionResetTask
from datagrowth.datatypes import DataStorages


@app.task(name="check_doi", base=DatabaseConnectionResetTask)
@atomic()
def check_doi(label: str, document_ids: List[int]):
    storages = DataStorages.from_label(label)
    for document in storages.Document.objects.filter(id__in=document_ids).select_for_update():
        document.derivatives["check_doi"] = {"check_doi": {"doi": "ok"}}
        document.task_results["check_doi"] = {"success": True}
        document.save()
