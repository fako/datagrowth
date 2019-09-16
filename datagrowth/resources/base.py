import logging

from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey, ContentType
from django.utils.timezone import datetime

from datagrowth import configuration


log = logging.getLogger("datascope")


class Resource(models.Model):

    # Identification
    uri = models.CharField(max_length=255, db_index=True, default=None)
    status = models.PositiveIntegerField(default=0)

    # Configuration
    config = configuration.ConfigurationField()

    # Archiving fields
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    purge_at = models.DateTimeField(null=True, blank=True)

    # Retention
    retainer = GenericForeignKey(ct_field="retainer_type", fk_field="retainer_id")
    retainer_type = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.CASCADE)
    retainer_id = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        abstract = True
        get_latest_by = "id"
        ordering = ("id",)

    def retain(self, retainer):
        self.retainer = retainer
        self.save()

    @property
    def content(self):
        raise NotImplementedError("Missing implementation for content property on {}".format(self.__class__.__name__))

    @classmethod
    def get_name(cls):
        return cls._meta.model_name
