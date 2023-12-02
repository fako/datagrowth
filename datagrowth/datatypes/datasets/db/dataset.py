from collections.abc import Iterator
from copy import deepcopy

from django.apps import apps
from django.db import models
from django.utils.timezone import now
from django.contrib.contenttypes.fields import GenericRelation

from datagrowth.configuration import ConfigurationField
from datagrowth.datatypes.storage import DataStorageFactory
from datagrowth.datatypes.datasets.db.version import DatasetVersionBase
from datagrowth.datatypes.datasets.constants import GrowthState, GrowthStrategy
from datagrowth.exceptions import DGGrowthUnfinished, DGPipelineError
from datagrowth.processors import HttpSeedingProcessor, SeedingProcessorFactory
from datagrowth.version import VERSION
from datagrowth.utils import ibatch


class DatasetBase(models.Model):

    signature = models.CharField(max_length=255, db_index=True)
    config = ConfigurationField()
    versions = GenericRelation(
        "DatasetVersion",
        content_type_field="dataset_type",
        object_id_field="dataset_id",
        related_query_name="datasets"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

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
        return {
            "document": self.DOCUMENT_TASKS,
            "collection": self.COLLECTION_TASKS,
            "datasetversion": self.DATASET_VERSION_TASKS
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

    def gather_seeds(self, *args):
        """
        This method can get overridden. Its output will be used as initial seeding for new DatasetVersions
        The ``grow`` method calls this method with all of its positional arguments

        :param args: arbitrary input from a call to ``growth``
        :return: iterator of dicts or Documents
        """
        return iter([])

    def weed_document(self, document):
        """
        This method can get overridden. Its output determines if a Document should get deleted before a new growth.
        It receives the Document to assess, but by default will retain all Documents

        :param document: Document to assess
        :return: whether to weed out the document or not
        """
        return False

    def seed(self, current_version, seeds):
        """
        Creates a new DatasetVersion with seeds as Documents in a Collection.
        Will include copies of Documents belonging to a previous DatasetVersion if it is given

        :param current_version: (DatasetVersion) A DatasetVersion which Documents should become part of.
        :param seeds: (list) Dicts or Documents that should become part of the new version
        :return:
        """
        # Check input and distill class
        DatasetVersion = current_version.__class__
        assert issubclass(DatasetVersion, DatasetVersionBase), \
            f"Expected current_version to be of type DatsetVersion not {type(current_version)}"
        assert isinstance(seeds, (Iterator, list, tuple,)), "Expected seeds to be a sequential iterable"
        # If version is in seeding state we simply add to it
        if GrowthState(current_version.state) is GrowthState.SEEDING:
            collection = current_version.collection_set.last()
            if not collection:
                raise DGPipelineError("Was unable to add seeds to Collection of DatasetVersion")
            collection.add(seeds)
            return current_version
        # In any other scenario we create a new version to add the seeds to
        new_version = DatasetVersion.objects.create(dataset=self, version=self.version, state=GrowthState.SEEDING)
        collection = new_version.collection_set.create(name=self.signature)
        collection.add(seeds)
        return new_version

    def grow(self, *args, seeds=None, asynchronous=True, grow_once=False):
        # We do nothing if a growth has already started asynchronously
        current_version = self.versions.filter(is_current=True).last()
        current_state = GrowthState(current_version.state)
        if current_version is None:
            current_version = self.versions.create(dataset=self, version=self.version, is_current=True)
        if current_state is GrowthState.GROWING and asynchronous:
            raise DGGrowthUnfinished()
        elif current_state is GrowthState.COMPLETE and grow_once:
            return True
        # Seeding a new DatasetVersion if necessary
        if current_state not in [GrowthState.SEEDING, GrowthState.GROWING]:
            seeds = seeds or []
            seeds += self.gather_seeds(*args)
            current_version = self.seed(current_version, seeds)
            if not current_version.document_set.exists():
                raise DGPipelineError(
                    "Expected the DatasetVersion to contain at least one Document after seeding"
                )
        current_version.state = GrowthState.GROWING
        current_version.save()
        # Now we actually start the growing process
        if asynchronous:
            raise DGGrowthUnfinished()

    def harvest_sample(self):
        pass

    def harvest(self):
        pass

    def __str__(self):
        return f"{self.signature} ({self.id})"

    class Meta:
        abstract = True
