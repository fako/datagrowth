from django.db import models

import json_field


class DataStorage(models.Model):

    schema = json_field.JSONField(default=dict, null=False, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

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
        raise NotImplementedError()

    def __str__(self):
        return "{} {}".format(self.__class__.__name__, self.id)

    class Meta:
        abstract = True
