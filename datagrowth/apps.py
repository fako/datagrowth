import importlib
import inspect

from django.apps import AppConfig, apps

from datagrowth.registry import DATAGROWTH_REGISTRY
from datagrowth.processors.base import Processor


class DatagrowthConfig(AppConfig):

    name = "datagrowth"

    def ready(self) -> None:
        self.load_processors()
        self.load_resources()

    def load_processors(self) -> None:

        DATAGROWTH_REGISTRY.clear_category("processor")
        registered_names: set[str] = set()
        datagrowth_names: set[str] = set()
        for app_config in apps.get_app_configs():
            try:
                processor_module = importlib.import_module(app_config.module.__name__ + ".processors")
                module_items = dict(processor_module.__dict__)
                for export_name in getattr(processor_module, "__all__", []):
                    if export_name in module_items:
                        continue
                    try:
                        module_items[export_name] = getattr(processor_module, export_name)
                    except AttributeError:
                        continue
                for name, attr in module_items.items():
                    if name in registered_names and name not in datagrowth_names:
                        raise RuntimeError("The {} Processor is being loaded twice".format(name))
                    if inspect.isclass(attr) and issubclass(attr, Processor):
                        DATAGROWTH_REGISTRY.register_processor(f"processor:{name}", attr)
                        registered_names.add(name)
                    if app_config.name == "datagrowth":
                        datagrowth_names.add(name)
            except ImportError:
                continue

    def load_resources(self) -> None:
        from datagrowth.resources.base import Resource

        DATAGROWTH_REGISTRY.clear_category("resource")
        for app_config in apps.get_app_configs():
            for model in app_config.get_models():
                if not issubclass(model, Resource):
                    continue
                if model._meta.abstract:
                    continue
                tag = f"resource:{model._meta.app_label}.{model._meta.model_name}"
                DATAGROWTH_REGISTRY.register_resource(tag, model)

    def get_processor_class(self, name: str) -> type | None:
        try:
            return DATAGROWTH_REGISTRY.get_class(f"processor:{name}")
        except KeyError:
            return None
