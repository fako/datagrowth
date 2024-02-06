import logging
from time import sleep

from datagrowth.management.base import DatasetCommand
from datagrowth.datatypes.datasets.constants import GrowthStrategy


log = logging.getLogger("datagrowth.command")


class Command(DatasetCommand):
    """
    Grows a Dataset
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('-g', '--growth-strategy', choices=GrowthStrategy, nargs="?")
        parser.add_argument('-s', '--synchronous', action="store_true")
        parser.add_argument('-l', '--limit', type=int, nargs="?")
        parser.add_argument('-r', '--retry', action="store_true")
        parser.add_argument('-i', '--initial-seeder', type=str, nargs="?")
        parser.add_argument('-t', '--timeout', type=int, default=60*60*24)
        parser.add_argument('-w', '--wait-interval', type=int, default=10)

    def get_datasets(self):
        raise TypeError("It is impossible to grow multiple datasets at the same time.")

    def handle_dataset(self, dataset, *args, **options):
        growth_strategy = options["growth_strategy"]
        asynchronous = not options["synchronous"]
        limit = options["limit"]
        retry = options["retry"]
        seeds = options["initial_seeder"]
        timeout = options["timeout"]
        wait_interval = options["wait_interval"]

        group_result = dataset.grow(
            *args,
            growth_strategy=growth_strategy, asynchronous=asynchronous, limit=limit, retry=retry, seeds=seeds
        )

        ready = not asynchronous or not group_result
        timer = 0
        while not ready and not timer >= timeout:
            ready = group_result.ready()
            sleep(wait_interval)
            timer += wait_interval
        else:
            if timer >= timeout:
                message = "Grow dataset command exceeded timeout"
                log.error(message)

    ###################################
    # Legacy Community compatability
    ###################################

    def handle_community(self, dataset, *args, **options):
        dataset.config = {"asynchronous": False}  # TODO: this is weird syntax as it is actually performing an update
        dataset.save()
        dataset.grow(*args)
        log.info("Result: {}".format(dataset.kernel))
        log.info("Growth: {}".format([growth.id for growth in dataset.growth_set.all()]))
