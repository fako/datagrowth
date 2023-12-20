from __future__ import annotations

from typing import Any, Type, Union, TYPE_CHECKING
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from datagrowth.datatypes.datasets.db.dataset import DatasetBase

from dataclasses import dataclass

from django.apps import apps

from datagrowth.datatypes.storage import DataStorage
from datagrowth.datatypes.documents.db.version import DatasetVersionBase
from datagrowth.datatypes.documents.db.collection import CollectionBase
from datagrowth.datatypes.documents.db.document import DocumentBase


@dataclass(slots=True)
class DataStorages:
    model: Any
    DatasetVersion: Type[DatasetVersionBase]
    Collection: Type[CollectionBase]
    Document: Type[DocumentBase]

    instance: Any = None
    dataset_version: DatasetVersionBase = None
    dataset: DatasetBase = None

    @classmethod
    def from_label(cls, label: str) -> DataStorages:
        model = apps.get_model(label)
        assert issubclass(model, DataStorage), f"Expected to load a DataStorage instance through label '{label}'"
        storages = cls(
            model=model,
            DatasetVersion=model.get_dataset_version_model(),
            Collection=model.get_collection_model(),
            Document=model.get_document_model()
        )
        return storages

    @classmethod
    def load_instances(cls, label: str, instance: Union[DataStorage, int], lock: bool = False):
        storages = cls.from_label(label)
        if isinstance(instance, DataStorage):
            assert not lock, "Can't lock an instance that is already loaded from the database"
            instance = instance
        else:
            # Instance is an integer id, which we'll use to fetch the instance.
            # We might perform a transaction lock when required.
            queryset = storages.model.objects.all()
            if lock:
                queryset.select_for_update()
            instance = queryset.get(id=instance)
        storages.instance = instance
        if hasattr(instance, "dataset_version"):
            storages.dataset_version = instance.dataset_version
            storages.dataset = instance.dataset_version.dataset
        elif hasattr(instance, "dataset"):
            storages.dataset = instance.dataset
        return storages
