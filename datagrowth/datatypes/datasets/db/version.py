from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from datagrowth.datatypes.datasets.constants import GrowthState


class DatasetVersionManager(models.Manager):

    def get_latest_version(self):
        return super().filter(is_current=True).last()


class DatasetVersionBase(models.Model):

    objects = DatasetVersionManager()

    dataset = GenericForeignKey(ct_field="dataset_type", fk_field="dataset_id")
    dataset_type = models.ForeignKey(ContentType, related_name="+", on_delete=models.PROTECT)
    dataset_id = models.PositiveIntegerField()

    is_current = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    version = models.CharField(max_length=50, null=False, blank=True)
    state = models.CharField(max_length=50, choices=[(state.value, state.value,) for state in GrowthState],
                             default=GrowthState.PENDING)

    def __str__(self):
        return "{} (v={}, id={})".format(self.dataset.signature, self.version, self.id)

    def copy_collection(self, collection):
        Document = collection.get_document_model()
        source_id = collection.id
        collection.pk = None
        collection.id = None
        collection.dataset_version = self
        collection.save()
        collection.add(Document.objects.filter(collection_id=source_id))
        return collection

    class Meta:
        abstract = True
        get_latest_by = "created_at"
