from typing import List, Union

from django.utils.timezone import now
from celery import current_app as app

from datagrowth.utils.tasks import DatabaseConnectionResetTask
from datagrowth.datatypes.types import DataStorages
from datagrowth.datatypes.documents.db.document import DocumentBase
from datagrowth.datatypes.documents.tasks.base import (load_pending_data_storages, validate_pending_data_storages,
                                                       dispatch_data_storage_tasks)


@app.task(name="growth.dispatch_document_tasks", base=DatabaseConnectionResetTask)
def dispatch_document_tasks(label: str, documents: List[Union[int, DocumentBase]], asynchronous: bool = True,
                            recursion_depth: int = 0) -> None:
    if not len(documents):
        return
    if recursion_depth >= 10:
        raise RecursionError("Maximum harvest_documents recursion reached")
    storages = DataStorages.from_label(label)
    documents = load_pending_data_storages(*documents, model=storages.Document, as_list=True)
    pending = validate_pending_data_storages(documents, model=storages.Document)
    if len(pending):
        recursive_callback_signature = dispatch_document_tasks.si(
            label,
            [doc.id for doc in documents],
            asynchronous=asynchronous,
            recursion_depth=recursion_depth+1
        )
        dispatch_data_storage_tasks(
            label,
            *pending,
            callback=recursive_callback_signature,
            asynchronous=asynchronous
        )


@app.task(name="growth.cancel_document_tasks", base=DatabaseConnectionResetTask)
def cancel_document_tasks(label: str, documents: List[Union[int, DocumentBase]]) -> None:
    if not len(documents):
        return
    storages = DataStorages.from_label(label)
    documents = load_pending_data_storages(*documents, model=storages.Document, as_list=True)
    if not documents:
        return

    documents = documents if isinstance(documents, list) else [documents]
    stopped = []
    for document in documents:
        for task in document.get_pending_tasks():
            document.task_results[task] = {"success": False, "canceled": True}
        document.pending_at = None
        document.finished_at = now()
        stopped.append(document)
    storages.Document.objects.bulk_update(stopped, ["pending_at", "finished_at", "pipeline"])


def start_document_tasks(documents: List[DocumentBase], asynchronous: bool = True) -> None:
    """
    A convenience function that starts background task dispatcher for given Document instances.

    :param documents: the Documents that should start processing tasks
    :param asynchronous: whether to process the set asynchronously
    :return: None
    """
    if not len(documents):
        return
    label = documents[0].get_label()
    if asynchronous:
        dispatch_document_tasks.delay(label, [doc.id for doc in documents], asynchronous=True)
    else:
        dispatch_document_tasks(label, [doc.id for doc in documents], asynchronous=False)
