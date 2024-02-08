from typing import Type, List, Union, Optional
from collections import defaultdict

from celery import signature, chord
from celery.canvas import Signature  # for type checking only

from datagrowth.exceptions import DGPendingDocuments, DGPendingCollections
from datagrowth.datatypes import DatasetVersionBase
from datagrowth.datatypes.storage import DataStorage


def load_pending_data_storages(*args, model: Type[DataStorage] = None,
                               as_list: bool = False) -> Union[List[DataStorage], DataStorage]:
    if not args:
        raise ValueError("load_pending_data_storages expects at least one model id or model instance")
    # We check that we didn't get already loaded instances and return them if we do
    if isinstance(args[0], model):
        if len(args) == 1 and not as_list:
            return args[0] if args[0].pending_at else None
        return [instance for instance in args if instance.pending_at]
    # When getting ids we load them from the database
    if len(args) == 1 and not as_list:
        return model.objects.filter(id=args[0], pending_at__isnull=False).first()
    return list(model.objects.filter(id__in=args, pending_at__isnull=False))


def validate_pending_data_storages(instances: Union[List[DataStorage], DataStorage],
                                   model: Type[DataStorage]) -> List[DataStorage]:
    if instances is None:
        return []
    instances = instances if isinstance(instances, list) else [instances]
    finished = []
    pending = []
    for instance in instances:
        # We skip any containers that have pending content
        if hasattr(instance, "documents") and instance.documents.filter(pending_at__isnull=False).exists():
            raise DGPendingDocuments()
        elif hasattr(instance, "collections") and instance.collections.filter(pending_at__isnull=False).exists():
            raise DGPendingCollections()
        # Then we check if the instance is done or is pending
        elif not instance.get_pending_tasks():
            instance.finish_processing(commit=False)
            finished.append(instance)
        else:
            pending.append(instance)
    update_fields = ["pending_at", "finished_at"]
    if issubclass(model, DatasetVersionBase):
        update_fields += ["is_current", "errors", "state"]
    model.objects.bulk_update(finished, update_fields)
    return pending


def dispatch_data_storage_tasks(label: str, *args, callback=Signature, asynchronous=True) -> Optional[Signature]:
    pending_tasks = defaultdict(list)
    for obj in args:
        for pending_task in obj.get_pending_tasks():
            pending_tasks[pending_task].append(obj.id)
    if not pending_tasks:
        return
    task_signatures = [signature(task_name, args=(label, obj_ids,)) for task_name, obj_ids in pending_tasks.items()]
    if asynchronous:
        return chord(task_signatures)(callback)
    for task in task_signatures:
        task()
    callback()
