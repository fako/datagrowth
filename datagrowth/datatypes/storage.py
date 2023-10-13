from copy import copy

from django.db import models
from django.urls import reverse
from django.utils.text import camel_case_to_spaces
from django.db.models import JSONField
from django.utils.timezone import now

from datagrowth.settings import DATAGROWTH_API_VERSION


class DataStorage(models.Model):

    tasks = JSONField(default=dict, blank=True)
    task_results = JSONField(default=dict, blank=True)
    derivatives = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    pending_at = models.DateTimeField(default=now, null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    @staticmethod
    def validate(data, schema):
        raise NotImplementedError()

    @property
    def content(self):
        raise NotImplementedError()

    def output(self, *args):
        raise NotImplementedError()

    @property
    def url(self):
        if not self.id:
            raise ValueError(f"Can't get url for unsaved {self.__class__.__name__}")
        app_name = self._meta.app_label.replace("_", "-")
        model_name = camel_case_to_spaces(self.__class__.__name__).replace(" ", "-")
        view_name = f"v{DATAGROWTH_API_VERSION}:{app_name}:{model_name}-content"
        return reverse(view_name, args=[self.id])

    def __str__(self):
        return "{} {}".format(self.__class__.__name__, self.id)

    class Meta:
        abstract = True


class DataStorageFactory:

    def __init__(self, **defaults):
        self.defaults = defaults

    def build(self, model, **kwargs):
        initialization = copy(self.defaults)
        initialization.update(kwargs)
        instance = model(**initialization)
        instance.clean()
        return instance
