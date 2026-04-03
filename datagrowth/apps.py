import importlib
import inspect

from django.apps import AppConfig, apps

from datagrowth.registry import DATAGROWTH_REGISTRY


class DatagrowthConfig(AppConfig):

    name = "datagrowth"

    def ready(self) -> None:
        self.load_processors()

    def load_processors(self) -> None:
        from datagrowth.processors.base import Processor

        DATAGROWTH_REGISTRY.clear_category("processor")
        registered_names: set[str] = set()
        datagrowth_names: set[str] = set()
        for app_config in apps.get_app_configs():
            try:
                processor_module = importlib.import_module(app_config.module.__name__ + ".processors")
                for name, attr in processor_module.__dict__.items():
                    if name in registered_names and name not in datagrowth_names:
                        raise RuntimeError("The {} Processor is being loaded twice".format(name))
                    if inspect.isclass(attr) and issubclass(attr, Processor):
                        DATAGROWTH_REGISTRY.register_processor(f"processor:{name}", attr)
                        registered_names.add(name)
                    if app_config.name == "datagrowth":
                        datagrowth_names.add(name)
            except ImportError:
                continue

    def get_processor_class(self, name: str) -> type | None:
        try:
            return DATAGROWTH_REGISTRY.get_class(f"processor:{name}")
        except KeyError:
            return None
