import importlib
import inspect

from django.apps import AppConfig, apps


class DatagrowthConfig(AppConfig):

    name = "datagrowth"
    processors = {}

    def ready(self):
        self.load_processors()

    def load_processors(self):
        from datagrowth.processors.base import Processor
        self.processors = {}
        datagrowth_processors = set()
        for app_config in apps.get_app_configs():
            try:
                processor_module = importlib.import_module(app_config.module.__name__ + ".processors")
                for name, attr in processor_module.__dict__.items():
                    if name in self.processors and name not in datagrowth_processors:
                        raise RuntimeError("The {} Processor is being loaded twice".format(name))
                    if inspect.isclass(attr) and issubclass(attr, Processor):
                        self.processors[name] = attr
                    if app_config.name == "datagrowth":
                        datagrowth_processors.add(name)
            except ImportError:
                continue

    def get_processor_class(self, name):
        return self.processors.get(name, None)
