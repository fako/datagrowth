from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from datagrowth.datatypes.storage import DataStorage
from datagrowth.datatypes.datasets.constants import GrowthState, GrowthStrategy


class DatasetVersionManager(models.Manager):

    def get_current_version(self):
        return super().filter(is_current=True).last()


class DatasetVersionBase(DataStorage):

    objects = DatasetVersionManager()

    dataset = GenericForeignKey(ct_field="dataset_type", fk_field="dataset_id")
    dataset_type = models.ForeignKey(ContentType, related_name="+", on_delete=models.PROTECT)
    dataset_id = models.PositiveIntegerField()

    growth_strategy = models.CharField(max_length=50, choices=GrowthStrategy.choices, default=GrowthStrategy.FREEZE)
    task_definitions = models.JSONField(default=dict, blank=True)

    is_current = models.BooleanField(default=False)
    version = models.CharField(max_length=50, null=False, blank=True)
    state = models.CharField(max_length=50, choices=GrowthState.choices, default=GrowthState.PENDING)

    @property
    def collections(self):
        return self.collection_set

    @property
    def documents(self):
        return self.document_set

    @classmethod
    def build(cls, dataset):
        instance = cls(
            dataset=dataset,
            growth_strategy=dataset.GROWTH_STRATEGY,
            task_definitions=dataset.get_task_definitions()
        )
        instance.clean()
        return instance

    def copy_collection(self, collection):
        Document = collection.get_document_model()
        source_id = collection.id
        collection.pk = None
        collection.id = None
        collection.dataset_version = self
        collection.clean()
        collection.save()
        collection.add_batches(Document.objects.filter(collection_id=source_id))
        return collection

    def influence(self, instance):
        if instance.dataset_version is None:  # possibly a Document passed on by a Collection
            instance.dataset_version = self
        model_name = instance._meta.model_name
        if model_name in self.task_definitions:
            instance.tasks = self.task_definitions[model_name]

    def __str__(self):
        return "{} (v={}, id={})".format(self.dataset.signature, self.version, self.id)

    class Meta:
        abstract = True
        get_latest_by = "created_at"
