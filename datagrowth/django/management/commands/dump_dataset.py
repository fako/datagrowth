from datagrowth.management.base import DatasetCommand


class Command(DatasetCommand):
    """
    Dumps a dataset by signature
    """

    def handle_dataset(self, dataset, *args, **options):
        dataset.to_file()
