import logging
import os
import re

from datagrowth.management.base import DatasetCommand
from datagrowth.utils import get_dumps_path


log = logging.getLogger("datagrowth.command")


class Command(DatasetCommand):
    """
    Loads a dataset by signature
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('-r', '--replace', action="store_true")

    def get_dataset(self):  # picks the correct dataset from all available datasets based on signature
        for dataset in self.get_datasets():
            if self.signature == dataset.signature:
                self.model = dataset
                return self.model

    def get_datasets(self):
        datasets = []
        for entry in os.scandir(get_dumps_path(self.model)):
            if entry.is_file() and not entry.name.startswith("."):
                instance = self.model()
                file_match = re.search(r"(?P<signature>.+?)\.?(?P<pk>\d+)?\.json$", entry.name)
                file_info = file_match.groupdict()
                instance.signature = file_info["signature"]
                instance.file_path = entry.path  # this property gets added especially for the command
                datasets.append(instance)
        return datasets

    def handle_dataset(self, dataset, *args, **options):
        replace = options["replace"]
        dataset.from_file(dataset.file_path, replace=replace)
