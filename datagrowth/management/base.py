from datetime import datetime
import logging

from django.apps import apps
from django.core.management.base import BaseCommand

from datagrowth.configuration import DecodeConfigAction


log = logging.getLogger("datagrowth.command")


class DatasetCommand(BaseCommand):
    """
    Base command for Dataset centered commands.

    If the ``cast_as_community`` class variable is True, this command by default will try to load a ``Community`` model,
    instead of a true ``Dataset`` and call ``handle_community`` instead of ``handle_dataset``.
    """
    dataset_model = ""

    model = None
    config = None
    signature = None
    cast_as_community = False

    def add_arguments(self, parser):
        parser.add_argument('dataset', type=str, nargs="?", default=self.dataset_model)
        parser.add_argument('-a', '--args', type=str, nargs="*", default="")
        parser.add_argument('-c', '--config', type=str, action=DecodeConfigAction, nargs="?", default={})
        parser.add_argument('-le', '--cast-as-community', type=str, nargs="?", default=self.cast_as_community)

    def set_attributes(self, *args, **options):
        self.cast_as_community = options.pop("cast_as_community")
        self.model = apps.get_model(options.pop("dataset"))
        self.config = options["config"]
        signature = getattr(self, "signature") or self.model().get_signature_from_input(*args, **self.config)
        self.signature = signature or None
        return options

    def handle_dataset(self, dataset, *arguments, **options):
        raise NotImplementedError("You should implement the handle_dataset method.")

    def handle_community(self, community, *arguments, **options):
        raise NotImplementedError("You should implement the handle_community method.")

    def get_dataset(self):
        if self.cast_as_community:
            community, created = self.model.objects.get_latest_or_create_by_signature(self.signature, **self.config)
            return community
        dataset, created = self.model.objects.get_or_create(signature=self.signature)
        return dataset

    def get_datasets(self):
        if self.cast_as_community:
            return self.model.objects.filter(state="Ready").iterator()
        return self.model.objects.all()

    def handle(self, *args, **options):
        options = self.set_attributes(*args, **options)

        if self.signature is not None:
            datasets = [self.get_dataset()]
        else:
            datasets = self.get_datasets()

        log.info(f"Target: {self.signature or self.model.__class__.__name__}")

        for dataset in datasets:
            log.info(f"Dataset: {dataset}")
            log.info(f"Start: {datetime.now()}")
            if self.cast_as_community:
                self.handle_community(dataset, *args, **options)
            else:
                self.handle_dataset(dataset, *args, **options)
            log.info(f"End: {datetime.now()}")
