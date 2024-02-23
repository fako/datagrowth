from typing import List
from datetime import datetime
from collections import defaultdict
from copy import copy

from django.apps import apps
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

    DOCUMENT_MODEL = "Document"
    COLLECTION_MODEL = "Collection"
    DATASET_VERSION_MODEL = "DatasetVersion"

    @classmethod
    def get_document_model(cls):
        return apps.get_model(f"{cls._meta.app_label}.{cls.DOCUMENT_MODEL}")

    @classmethod
    def get_collection_model(cls):
        return apps.get_model(f"{cls._meta.app_label}.{cls.COLLECTION_MODEL}")

    @classmethod
    def get_dataset_version_model(cls):
        return apps.get_model(f"{cls._meta.app_label}.{cls.DATASET_VERSION_MODEL}")

    @classmethod
    def get_label(cls):
        return f"{cls._meta.app_label}.{cls._meta.model_name}"

    @classmethod
    def build(cls, *args):
        raise NotImplementedError()

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

    def get_pending_tasks(self) -> List[str]:
        pending_tasks = []
        for task_name, conditions in self.tasks.items():
            # If a task has already run it can't be pending to prevent eternal loops
            has_run = self.task_results.get(task_name, False)
            # Check attributes on the object to see if this task is pending
            is_pending_task = False
            for check in conditions["checks"]:
                negate = check.startswith("!")
                check_attribute = getattr(self, check if not negate else check[1:])
                if not check_attribute and not negate or check_attribute and negate:
                    break
            else:
                is_pending_task = True
            # Check if dependencies for the task are met
            has_met_dependencies = True
            for dependency in conditions["depends_on"]:
                # Dependencies based on content we skip in this abstract method (where content is not always available)
                if dependency.startswith("$"):
                    continue
                # Dependencies based on other tasks are checked through the pipeline attribute
                if not self.task_results.get(dependency, {}).get("success"):
                    has_met_dependencies = False
                    break
            # Only if all conditions are satisfied we consider the task pending
            if not has_run and is_pending_task and has_met_dependencies:
                pending_tasks.append(task_name)
        return pending_tasks

    def get_property_dependencies(self) -> dict:
        property_dependencies = defaultdict(list)
        for task_name, conditions in self.tasks.items():
            for dependency in conditions.get("depends_on", []):
                if dependency.startswith("$"):
                    property_dependencies[dependency].append(task_name)
        return property_dependencies

    def invalidate_task(self, task_name: str, current_time: datetime = None, commit: bool = False) -> None:
        if task_name in self.task_results:
            del self.task_results[task_name]
        if task_name in self.derivatives:
            del self.derivatives[task_name]
        self.pending_at = current_time or now()
        self.finished_at = None
        if commit:
            self.save()

    def finish_processing(self, current_time: datetime = None, commit: bool = True):
        self.pending_at = None
        self.finished_at = current_time or now()
        if commit:
            self.save()

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
