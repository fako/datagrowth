from typing import List

from django.conf import settings
from django.db.transaction import atomic
from celery import current_app as app

from datagrowth.utils.tasks import DatabaseConnectionResetTask
from datagrowth.datatypes import DataStorages


@app.task(name="check_doi", base=DatabaseConnectionResetTask)
@atomic()
def check_doi(label: str, document_ids: List[int]):
    storages = DataStorages.from_label(label)
    for document in storages.Document.objects.filter(id__in=document_ids).select_for_update():
        if document.identity not in settings.TEST_CHECK_DOI_FAILURE_IDENTITIES:
            message = "ok"
            success = True
        else:
            message = "fail"
            success = False
        document.derivatives["check_doi"] = {"check_doi": {"doi": message}}
        document.task_results["check_doi"] = {"success": success}
        document.save()
