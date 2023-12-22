import logging
from typing import List, Dict, Union
from datetime import datetime

from django.utils.timezone import now
from celery import current_app as app

from datagrowth.exceptions import DGPendingDocuments
from datagrowth.configuration import ConfigurationType, load_config
from datagrowth.utils import ibatch
from datagrowth.utils.tasks import DatabaseConnectionResetTask
from datagrowth.datatypes.types import DataStorages
from datagrowth.datatypes.documents.db.collection import CollectionBase
from datagrowth.datatypes.documents.tasks.base import (load_pending_data_storages, validate_pending_data_storages,
                                                       dispatch_data_storage_tasks)
from datagrowth.datatypes.documents.tasks.dataset_version import dispatch_dataset_version_tasks

from datagrowth.datatypes.documents.tasks.document import start_document_tasks, cancel_document_tasks
from datagrowth.processors import ProcessorFactory


log = logging.getLogger("datagrowth.growth")


def dispatch_collection_task_retry(task, exc, task_id, args, kwargs, einfo):
    if task.request.retries == task.max_retries:
        label = args[0]
        collection_id = args[1]
        storages = DataStorages.load_instances(label, collection_id)
        collection = storages.instance
        if not load_pending_data_storages(collection, model=storages.Collection):
            log.warning("Couldn't load pending Collection during on_retry of dispatch_collection_tasks")
            return
        pending_document_count = collection.documents.filter(pending_at__isnull=False).count()
        log.info(f"Cancelling document tasks for {pending_document_count} documents")
        for batch in ibatch(collection.documents.filter(pending_at__isnull=False).iterator(), batch_size=100):
            cancel_document_tasks(storages.Document.get_label(), batch)


@app.task(
    name="growth.dispatch_collection_tasks",
    base=DatabaseConnectionResetTask,
    autoretry_for=(DGPendingDocuments,),
    retry_kwargs={"max_retries": 5, "countdown": 5 * 60},
    on_retry=dispatch_collection_task_retry
)
def dispatch_collection_tasks(label: str, collection: Union[int, CollectionBase], asynchronous: bool = True,
                              recursion_depth: int = 0) -> None:
    if recursion_depth >= 10:
        raise RecursionError("Maximum dispatch_collection_tasks recursion reached")
    storages = DataStorages.load_instances(label, collection)
    collection = storages.instance
    if not load_pending_data_storages(collection, model=storages.Collection):
        # parallel tasks may already picked-up this dispatch and nothing should be processed
        return

    # Dispatch pending tasks
    pending = validate_pending_data_storages(collection, model=storages.Collection)
    if len(pending):
        recursive_callback_signature = dispatch_collection_tasks.si(
            label,
            collection.id,
            asynchronous=asynchronous,
            recursion_depth=recursion_depth+1
        )
        dispatch_data_storage_tasks(
            label,
            *pending,
            callback=recursive_callback_signature,
            asynchronous=asynchronous
        )
    elif validate_pending_data_storages(storages.dataset_version, model=storages.DatasetVersion):
        dataset_version_callback_signature = dispatch_dataset_version_tasks.si(
            collection.dataset_version.get_label(),
            collection.dataset_version_id,
            asynchronous=asynchronous,
            recursion_depth=recursion_depth+1
        )
        dispatch_data_storage_tasks(
            label,
            collection.dataset_version,
            callback=dataset_version_callback_signature,
            asynchronous=asynchronous
        )


def start_collection_tasks(collection: CollectionBase, start_time: datetime, asynchronous: bool = True) -> None:
    """
    A convenience function that sets the state of Collection to pending and starts background task dispatcher.

    :param collection: the Collection that should start processing tasks
    :param start_time: the time the Set should be considered pending
    :param asynchronous: whether to process the set asynchronously
    :return: None
    """
    collection.pending_at = start_time
    collection.clean()
    collection.save()
    if asynchronous:
        dispatch_collection_tasks.delay(collection.get_label(), collection.id, asynchronous=True)
    else:
        dispatch_collection_tasks(collection.get_label(), collection.id, asynchronous=False)


@app.task(name="growth.grow_collection", base=DatabaseConnectionResetTask)
@load_config()
def grow_collection(config: ConfigurationType, label: str, collection_id: int, *args, asynchronous: bool = True,
                    seeds: Union[List[Dict], str] = None, limit: int = None):
    current_time = now()
    storages = DataStorages.load_instances(label, collection_id)
    collection = storages.instance
    if storages.instance.pending_at is not None:
        log.warning(
            f"Collection '{collection.name}' is already pending since {collection.pending_at} and will not grow again"
        )
        return

    # Process any documents that already have a pending state due to previous task failures
    log.info(f"Starting tasks for documents from: {label}, {collection.name}")
    pending_documents = collection.documents.filter(pending_at__isnull=False)
    for documents in ibatch(pending_documents.iterator(), batch_size=config.batch_size):
        start_document_tasks(documents, asynchronous=asynchronous)

    # Load initial seeds through processor if necessary
    if isinstance(seeds, str):
        initial_factory = ProcessorFactory(seeds)
        prc, create_seeds = initial_factory.build_with_callable(config)
        seeds = create_seeds()

    # Process new seeds to documents
    if limit == -1:
        # A limit of -1 indicates that this task shouldn't try to gather more seeds for growing
        seeding = []
    else:
        # By default we'll use a seeding factory from the Dataset to gather more seeds for growing
        factories = storages.dataset.get_seeding_factories()
        seeding_factory = factories[collection.name]
        seeding_processor = seeding_factory.build(config=config, collection=collection, initial=seeds)
        seeding = seeding_processor(*args)

    log.info(f"Starting seeding: {label}, {collection.name}")
    count = 0
    for documents in seeding:
        start_document_tasks(documents, asynchronous=asynchronous)
        count += len(documents)
        if limit is not None and count >= limit:
            break

    log.info(f"Starting tasks for: {label}, {collection.name}")
    start_collection_tasks(collection, current_time, asynchronous=asynchronous)
