from copy import copy

from django.db import models
from django.contrib.contenttypes.fields import GenericRelation

from datagrowth.configuration import ConfigurationField
from datagrowth.datatypes.datasets.constants import GrowthState
from datagrowth.exceptions import DGGrowthUnfinished, DGPipelineError
from datagrowth.version import VERSION


class DatasetBase(models.Model):

    signature = models.CharField(max_length=255, db_index=True)
    config = ConfigurationField()
    versions = GenericRelation("DatasetVersion", content_type_field="dataset_type", object_id_field="dataset_id")

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    NAME = None

    @property
    def pipelines(self):
        return {
            "seeder": None,
            "growth": [],
            "harvest": []
        }

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
        growth_processors = copy(self.pipelines.get("growth", []))
        seeder_processor = self.pipelines.get("seeder", None)
        if seeder_processor:
            growth_processors.append(seeder_processor)
        for processor in growth_processors:
            growth_keys.update({key[1:] for key, value in processor.config.items() if key.startswith("$")})
        # Actual filtering of input
        return {key: value for key, value in kwargs.items() if key.strip("$") in growth_keys}

    def filter_harvest_configuration(self, **kwargs):
        # Calculate which keys are whitelisted
        harvest_keys = set()
        for processor in self.pipelines.get("harvest", []):
            harvest_keys.update({key[1:] for key, value in processor.config.items() if key.startswith("$")})
        # Actual filtering of input
        return {key: value for key, value in kwargs.items() if key.strip("$") in harvest_keys}

    def gather_seeds(self, *args):
        """
        This method can get overridden. Its output will be used as initial seeding for new DatasetVersions
        The ``grow`` method calls this method with all of its positional arguments

        :param args: arbitrary input from a call to ``growth``
        :return: iterator of dicts or Documents
        """
        return iter([])

    def refine_seeds(self, document_queryset):
        """
        This method can get overridden. Its output will be used as seeding for new DatasetVersions
        A Documents queryset from the last DatasetVersion gets passed into this method,
        but by default it returns an empty iterator.

        :param document_queryset: Document queryset from the last DatasetVersion
        :return: iterator of dicts or Documents
        """
        return iter([])

    def seed(self, current_version, seeds):
        """
        Creates a new DatasetVersion with seeds as Documents in a Collection.
        Will include copies of Documents belonging to a previous DatasetVersion if it is given

        :param current_version: (DatasetVersion) A DatasetVersion which Documents should become part of.
        :param seeds: (list) Dicts or Documents that should become part of the new version
        :return:
        """
        # If version is in seeding state we simply add to it
        if current_version.state == GrowthState.SEEDING:
            collection = current_version.collection_set.last()
            if not collection:
                raise DGPipelineError("Was unable to add seeds to Collection of DatasetVersion")
            collection.add(seeds)
            return current_version
        # In any other scenario we create a new version to add the seeds to
        new_version = current_version.objects.create(dataset=self, version=self.version, state=GrowthState.SEEDING)
        collection = new_version.collection_set.create(name=self.signature)
        collection.add(seeds)
        return new_version

    def grow(self, *args, seeds=None):
        # We do nothing if a growth has already started
        current_version = self.versions.get_latest_version()
        if current_version is None:
            current_version = self.versions.create(dataset=self, version=self.version, is_current=True)
        if current_version.state == GrowthState.GROWING:
            raise DGGrowthUnfinished()
        # Seeding a new DatasetVersion Checking input to make sure that there is something to do
        if current_version.state != GrowthState.SEEDING:
            seeds = seeds or []
            seeds += self.gather_seeds(*args)
            current_version = self.seed(current_version, seeds)
            if not current_version.document_set.exists():
                raise DGPipelineError(
                    "Expected the DatasetVersion to contain at least one Document after seeding"
                )
        current_version.state = GrowthState.GROWING
        current_version.save()

    def harvest_sample(self):
        pass

    def harvest(self):
        pass

    def __str__(self):
        return f"{self.signature} ({self.id})"

    class Meta:
        abstract = True
