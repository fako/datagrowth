from typing import Optional
import os
from copy import deepcopy

from django.apps import apps
from django.db import models
from django.utils.timezone import now
from django.contrib.contenttypes.fields import GenericRelation
from celery import group
from celery.canvas import GroupResult  # for type checking only

from datagrowth.configuration import ConfigurationField
from datagrowth.exceptions import DGGrowthUnfinished, DGGrowthFrozen
from datagrowth.datatypes.storage import DataStorageFactory
from datagrowth.datatypes.datasets.constants import GrowthState, GrowthStrategy
from datagrowth.datatypes.documents.tasks.collection import grow_collection
from datagrowth.processors import HttpSeedingProcessor, SeedingProcessorFactory
from datagrowth.resources.utils import update_serialized_resources
from datagrowth.version import VERSION
from datagrowth.utils import ibatch, get_dumps_path, object_to_disk, queryset_to_disk, objects_from_disk


class DatasetBase(models.Model):

    signature = models.CharField(max_length=255, db_index=True, unique=True)
    config = ConfigurationField()
    versions = GenericRelation(
        "DatasetVersion",
        content_type_field="dataset_type",
        object_id_field="dataset_id",
        related_query_name="datasets"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    #######################################################
    # DATASET CONFIGURATION CONSTANTS AND METHODS
    #######################################################
    # Attributes that may get set for a Dataset to configure its behaviour.
    # It's also possible to override the methods that use the constant attributes to compute the configurations.

    NAME = None
    CONFIG = {}

    GROWTH_STRATEGY = GrowthStrategy.FREEZE
    SEEDING_PHASES = []
    DOCUMENT_TASKS = {}
    COLLECTION_TASKS = {}
    DATASET_VERSION_TASKS = {}
    HARVEST_PHASES = []

    COLLECTION_IDENTIFIER = "id"
    COLLECTION_REFEREE = None
    DATASET_VERSION_MODEL = "DatasetVersion"

    def get_seeding_configurations(self):
        seeding_configurations = []
        for phase_name, factory in self.get_seeding_factories().items():
            for configs in factory.processor.create_phase_configurations(factory.defaults["phases"]):
                for config in configs.values():
                    seeding_configurations.append(config)
        return seeding_configurations

    def get_seeding_factories(self):
        assert self.SEEDING_PHASES, "Expected Dataset to specify SEEDING_PHASES"
        return {
            self.signature: SeedingProcessorFactory(HttpSeedingProcessor, self.SEEDING_PHASES)
        }

    def get_collection_factories(self):
        return {
            phase_name: DataStorageFactory(identifier=self.COLLECTION_IDENTIFIER, referee=self.COLLECTION_REFEREE)
            for phase_name in self.get_seeding_factories().keys()
        }

    def get_task_definitions(self):
        DatasetVersion = self.get_dataset_version_model()
        Collection = DatasetVersion.get_collection_model()
        Document = DatasetVersion.get_document_model()
        return {
            Document._meta.model_name: self.DOCUMENT_TASKS,
            Collection._meta.model_name: self.COLLECTION_TASKS,
            DatasetVersion._meta.model_name: self.DATASET_VERSION_TASKS
        }

    @classmethod
    def get_dataset_version_model(cls):
        return apps.get_model(f"{cls._meta.app_label}.{cls.DATASET_VERSION_MODEL}")

    @property
    def version(self):
        return VERSION

    @classmethod
    def get_name(cls):
        if cls.NAME:
            return cls.NAME
        word_separator = '_'
        class_name = cls.__name__
        class_name = class_name.replace('Dataset', '')
        if not class_name:
            class_name = "Dataset"
        name = ''
        for index, char in enumerate(class_name):
            if char.isupper():
                name += word_separator + char.lower() if not index == 0 else char.lower()
            else:
                name += char
        return name

    @classmethod
    def get_namespace(cls):
        return cls._meta.app_label.replace("_", "-")

    def get_signature_from_input(self, *args, **kwargs):
        growth_configuration = self.filter_growth_configuration(**kwargs)
        signature = list(args) + [f"{key}={value}" for key, value in growth_configuration.items()]
        signature = list(filter(bool, signature))
        signature.sort()
        return "&".join(signature)

    def filter_growth_configuration(self, **kwargs):
        # Calculate which keys are whitelisted
        growth_keys = set()
        growth_configs = self.get_seeding_configurations()
        growth_configs.append(self.CONFIG)
        for config in growth_configs:
            growth_keys.update({key[1:] for key, value in config.items() if key.startswith("$")})
        # Actual filtering of input
        return {key: value for key, value in kwargs.items() if key.strip("$") in growth_keys}

    def filter_harvest_configuration(self, **kwargs):
        # Calculate which keys are whitelisted
        harvest_keys = set()
        harvest_configs = [factory.defaults for factory in self.HARVEST_PHASES]
        harvest_configs.append(self.CONFIG)
        for config in harvest_configs:
            harvest_keys.update({key[1:] for key, value in config.items() if key.startswith("$")})
        # Actual filtering of input
        return {key: value for key, value in kwargs.items() if key.strip("$") in harvest_keys}

    #######################################################
    # DATASET VERSION MANIPULATION
    #######################################################
    # Methods that work with DatasetVersions

    def create_dataset_version(self):
        DatasetVersion = self.get_dataset_version_model()
        Collection = DatasetVersion.get_collection_model()
        dataset_version = DatasetVersion.build(self)
        dataset_version.pending_at = None
        dataset_version.save()
        collections = []
        for collection_name, factory in self.get_collection_factories().items():
            collection = factory.build(
                Collection,
                name=collection_name,
                dataset_version=dataset_version,
                pending_at=None
            )
            collections.append(collection)
        Collection.objects.bulk_create(collections)
        return dataset_version

    @staticmethod
    def copy_dataset_version(dataset_version):
        collections = list(dataset_version.collections.all())
        dataset_version = deepcopy(dataset_version)
        dataset_version.pk = None
        dataset_version.id = None
        dataset_version.clean()
        dataset_version.save()
        for collection in collections:
            dataset_version.copy_collection(collection)
        return dataset_version

    def prepare_dataset_version(self, dataset_version, current_time=None):
        DatasetVersion = self.get_dataset_version_model()
        Document = DatasetVersion.get_document_model()
        current_time = current_time or now()

        dataset_version.state = GrowthState.PENDING
        dataset_version.pending_at = current_time
        dataset_version.finished_at = None
        dataset_version.task_results = {}
        dataset_version.derivatives = {}
        dataset_version.save()

        for batch in ibatch(dataset_version.documents.all(), batch_size=100):
            documents = []
            invalid_document_ids = []
            for document in batch:
                for task in document.tasks.keys():
                    result = document.task_results.get(task, {})
                    if not result.get("success"):
                        document.invalidate_task(task, current_time=current_time)
                if self.weed_document(document):
                    invalid_document_ids.append(document.id)
                else:
                    documents.append(document)
            Document.objects.filter(id__in=invalid_document_ids).delete()
            Document.objects.bulk_update(documents, ["task_results", "derivatives", "pending_at", "finished_at"])

        dataset_version.collections.update(pending_at=None, finished_at=None, task_results={}, derivatives={})

        return dataset_version

    #######################################################
    # DATASET GROWTH
    #######################################################
    # Methods that enable a Dataset to expand its data.

    def ennoble_seeds(self, *args):
        """
        This method can get overridden. Its output will be used as initial seeding.
        The ``grow`` method calls this method with all of its positional arguments

        :param args: arbitrary input from a call to ``growth``
        :return: list of dicts/Documents or Processor method as string to generate dicts
        """
        return []

    def weed_document(self, document):
        """
        This method can get overridden. Its output determines if a Document should get deleted before a new growth.
        It receives the Document to assess, but by default will retain all Documents

        :param document: Document to assess
        :return: whether to weed out the document or not
        """
        return False

    def prepare_growth(self, growth_strategy, current_version=None, retry=False):
        if not current_version or growth_strategy in [GrowthStrategy.RESET, GrowthStrategy.STACK]:
            current_version = self.create_dataset_version()
            current_version = self.prepare_dataset_version(current_version)
        elif retry:
            current_version = self.prepare_dataset_version(current_version)
        elif growth_strategy == GrowthStrategy.REVISE:
            current_version = self.copy_dataset_version(current_version)
            current_version = self.prepare_dataset_version(current_version)
        else:
            raise ValueError(f"Unknown growth_strategy to prepare for: {growth_strategy}")
        return current_version

    def dispatch_growth(self, dataset_version, *args, asynchronous=True, retry=False, seeds=None,
                        limit=None) -> Optional[GroupResult]:
        # Decide on whether to start the growth or exit, because a growth is already in progress
        if dataset_version.state == GrowthState.GROWING:
            raise DGGrowthUnfinished()
        dataset_version.state = GrowthState.GROWING
        dataset_version.save()

        grow_signatures = []
        for collection in dataset_version.collections.all():
            has_documents = collection.documents.exists()
            label = collection.get_label()

            # Determine what to do with parameters to grow_collection task
            # We only pass seeds to grow_collection when the DatasetVersion has no historic data.
            if dataset_version.state == GrowthState.PENDING and not has_documents:
                seeds = seeds or self.ennoble_seeds()
            else:
                seeds = None
            # When the limit is set to -1 no new Documents will be created and only the tasks will be retried.
            # This is the default for retry when Documents exist
            if retry and has_documents and limit is None:
                seeding_limit = -1
            else:
                seeding_limit = limit

            # Create the signatures for dispatching
            grow_signature = grow_collection.s(
                label, collection.id, *args,
                asynchronous=asynchronous, seeds=seeds, limit=seeding_limit,
                config=self.config.to_dict(protected=True, private=True)
            )
            grow_signatures.append(grow_signature)

        if asynchronous:
            return group(grow_signatures).delay()
        for task in grow_signatures:
            task()

    def grow(self, *args, growth_strategy=None, asynchronous=True, retry=False, seeds=None,
             limit=None) -> Optional[GroupResult]:
        # Set argument defaults
        growth_strategy = growth_strategy or self.GROWTH_STRATEGY
        dataset_version_filters = {} if growth_strategy == GrowthStrategy.STACK else {"is_current": True}
        current_version = self.versions.filter(**dataset_version_filters).last()

        # Decide on growth preparation
        # After this current_version should never be None and any new DatasetVersions will be PENDING.
        # Any GROWING datasets still get passed through, but will raise exceptions from dispatch_growth.
        if growth_strategy == GrowthStrategy.FREEZE and current_version:
            # Updates of frozen data is forbidden
            raise DGGrowthFrozen()
        elif current_version is None or current_version.state == GrowthState.COMPLETE:
            # There is no current DatasetVersion or it has completed in the past.
            # We'll start a new DatasetVersion with PENDING state.
            # It's either a copy of the last DatasetVersion or an empty DatasetVersion (depending on the strategy)
            current_version = self.prepare_growth(growth_strategy, current_version=current_version, retry=False)
        elif retry and current_version.state != GrowthState.GROWING:
            # When DatasetVersion.state is PENDING or ERROR a retry of a growth will keep the current DatasetVersion.
            # Except it will remove faulty Documents as well as all task history to allow tasks to run again.
            current_version = self.prepare_growth(growth_strategy, current_version=current_version, retry=True)

        # Now we actually start the growing process
        return self.dispatch_growth(
            current_version, *args,
            asynchronous=asynchronous,
            retry=retry,
            seeds=seeds,
            limit=limit
        )

    def handle_seeding_error(self, collection, exception):
        if dataset_version := collection.dataset_version:
            update_serialized_resources(dataset_version.errors["seeding"], exception.resource)
            dataset_version.save()

    #######################################################
    # DATASET HARVEST
    #######################################################
    # Methods that handle how a fully grown Dataset may export its data through a harvest.

    def harvest_sample(self):
        pass

    def harvest(self):
        pass

    #######################################################
    # DATASET RAW IO
    #######################################################
    # Methods that handle how a fully grown Dataset may export its data through a harvest.

    def to_querysets(self):
        # Loading models
        DatasetVersion = self.get_dataset_version_model()
        Collection = DatasetVersion.get_collection_model()
        Document = DatasetVersion.get_document_model()
        # Load DatasetVersion instances based on GROWTH_STRATEGY
        dataset_version_filters = {} if self.GROWTH_STRATEGY == GrowthStrategy.STACK else {"is_current": True}
        versions_set = self.versions.filter(**dataset_version_filters)
        version_ids = versions_set.values_list("id", flat=True)
        # Load other data based on the DatasetVersion
        collection_set = Collection.objects.filter(dataset_version_id__in=version_ids)
        document_set = Document.objects.filter(dataset_version_id__in=version_ids)
        # Return QuerySets
        return versions_set, collection_set, document_set

    @property
    def collections(self):
        dvs, cols, docs = self.to_querysets()
        return cols

    @property
    def documents(self):
        dvs, cols, docs = self.to_querysets()
        return docs

    def to_file(self, batch_size=100, progress_bar=True):
        destination = get_dumps_path(self)
        if not os.path.exists(destination):
            os.makedirs(destination)
        file_name = os.path.join(destination, f"{self.signature}.{self.id}.json")
        with open(file_name, "w") as json_file:
            object_to_disk(self, json_file)
            dataset_versions, collections, documents = self.to_querysets()
            queryset_to_disk(dataset_versions, json_file, batch_size=batch_size, progress_bar=progress_bar)
            queryset_to_disk(collections, json_file, batch_size=batch_size, progress_bar=progress_bar)
            queryset_to_disk(documents, json_file, batch_size=batch_size, progress_bar=progress_bar)

    @classmethod
    def from_file(cls, file_path, replace=False, progress_bar=True):
        # Basic path check
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"No dump exists at: {file_path}")
        # Preset model and instance variables
        dataset = None
        DatasetVersion = None
        Collection = None
        Document = None
        # Preset id containers
        dataset_version_ids = {}
        collection_ids = {}
        # Start reading the file
        with open(file_path, "r") as dump_file:
            for objects in objects_from_disk(dump_file, progress_bar=progress_bar):
                # Handling no objects makes no sense
                if not len(objects):
                    continue

                # When we can blindly replace all data
                # Then we delete/add the objects and ignore everything else in this loop
                if replace:
                    obj = objects[0]
                    model = type(obj)
                    model.objects.filter(id__in=[obj.id for obj in objects]).delete()
                    model.objects.bulk_create(objects)
                    continue

                # We'll decide what to do based on type of the first object
                obj = objects[0]
                # Datasets we want to use for determining types,
                # as well as saving it and possible changes based on signatures
                if isinstance(obj, DatasetBase):
                    dataset = obj
                    Dataset = type(obj)
                    DatasetVersion = Dataset.get_dataset_version_model()
                    Collection = DatasetVersion.get_collection_model()
                    Document = DatasetVersion.get_document_model()
                    original = Dataset.objects.get(signature=obj.signature)
                    if original:
                        original.versions.update(is_current=False)
                        dataset.id = original.id
                    dataset.save()
                # DatasetVersions need to store the correct Dataset relation.
                # And we'll possibly need to map Collections and Documents to new DatasetVersion ids.
                elif isinstance(obj, DatasetVersion):
                    for dataset_version in objects:
                        dump_id = dataset_version.id
                        dataset_version.pk = None
                        dataset_version.id = None
                        dataset_version.dataset = dataset
                        dataset_version.save()
                        dataset_version_ids[dump_id] = dataset_version.id
                # Collections need to store the correct DatasetVersion relation.
                # And we'll possibly need to map Documents to new Collection ids.
                elif isinstance(obj, Collection):
                    for collection in objects:
                        dump_id = collection.id
                        collection.pk = None
                        collection.id = None
                        collection.dataset_version_id = dataset_version_ids[collection.dataset_version_id]
                        collection.save()
                        collection_ids[dump_id] = collection.id
                # For Documents we only need to update ids of relations
                elif isinstance(obj, Document):
                    for document in objects:
                        document.pk = None
                        document.id = None
                        document.dataset_version_id = dataset_version_ids[document.dataset_version_id]
                        document.collection_id = collection_ids[document.collection_id]
                    Document.objects.bulk_create(objects)

        return dataset

    #######################################################
    # UTILITY
    #######################################################
    # Some standard methods to work easier with Datasets

    def __str__(self):
        return f"{self.signature} ({self.id})"

    class Meta:
        abstract = True
