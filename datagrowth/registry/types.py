from __future__ import annotations

from typing import cast
import importlib
from dataclasses import dataclass, field
from pydantic import BaseModel

from datagrowth.protocols import ProcessorProtocol
from datagrowth.resources.protocols import ResourceProtocol
from datagrowth.configuration import ConfigurationType, create_config


def _import_class(path: str) -> type:
    """
    Helper function that takes a qualname of a class and imports it.
    Will indicate where the import path breaks when errors occur.
    """
    parts = path.split(".")
    for index in range(len(parts) - 1, 0, -1):
        module_name = ".".join(parts[:index])
        attr_path = parts[index:]
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as error:
            if error.name == module_name:
                continue
            raise
        clazz = module
        for attribute in attr_path:
            clazz = getattr(clazz, attribute)
        if not isinstance(clazz, type):
            raise TypeError(f"Expected class import from path '{path}', got {type(clazz)}")
        return clazz
    raise ImportError(f"Could not import class path '{path}'")


class Tag(BaseModel):
    category: str
    value: str

    @classmethod
    def from_strings(cls, *args: str) -> list[Tag]:
        return [cls.from_string(string) for string in args]

    @classmethod
    def from_string(cls, string: str) -> Tag:
        assert string.count(":") == 1, \
            "Expected Tag string to contain a single semicolon separating categories and values"
        category, value = string.split(":")
        return cls(category=category.lower(), value=value.lower())

    #####################
    # Pydantic plumbing
    #####################

    model_config = {
        "frozen": True
    }

    def __str__(self) -> str:
        return f"{self.category}:{self.value}"

    def __hash__(self) -> int:
        return hash(str(self))


@dataclass
class Registry:
    tags: dict[str, Tag] = field(default_factory=dict)
    classes: dict[Tag, str] = field(default_factory=dict)
    configurations: dict[Tag, ConfigurationType] = field(default_factory=dict)

    #####################
    # Tags
    #####################

    @classmethod
    def from_tags(cls, tags: list[Tag]) -> Registry:
        return Registry(
            tags={str(tag): tag for tag in tags}
        )

    def register_tag(self, tag: str | Tag) -> Tag:
        if isinstance(tag, str):
            tag = Tag.from_string(tag)
        self.tags[str(tag)] = tag
        return tag

    def unregister_tag(self, tag: str | Tag) -> None:
        if isinstance(tag, Tag):
            tag = str(tag)
        del self.tags[tag]

    def tags_by_category(self, category: str) -> list[Tag]:
        return [tag for tag in self.tags.values() if tag.category == category]

    def tags_by_value(self, value: str) -> list[Tag]:
        return [tag for tag in self.tags.values() if tag.value == value]

    def clear_category(self, category: str) -> None:
        for tag in self.tags_by_category(category):
            self.classes.pop(tag, None)
            self.configurations.pop(tag, None)
            del self.tags[str(tag)]

    #####################
    # Classes
    #####################

    def register_class(self, tag: str | Tag, clazz: type) -> Tag:
        if isinstance(tag, str):
            tag = Tag.from_string(tag)
        tag = self.register_tag(tag)
        self.classes[tag] = f"{clazz.__module__}.{clazz.__qualname__}"
        return tag

    def unregister_class(self, tag: str | Tag) -> None:
        if isinstance(tag, str):
            tag = Tag.from_string(tag)
        del self.classes[tag]

    def get_class(self, tag: str | Tag) -> type:
        if isinstance(tag, str):
            tag = Tag.from_string(tag)
        return _import_class(self.classes[tag])

    #####################
    # Configurations
    #####################

    @staticmethod
    def _normalize_config(namespace: str | list[str],
                          config: ConfigurationType | dict | None) -> ConfigurationType | None:
        if not config:
            return None
        elif isinstance(config, ConfigurationType):
            return config
        return create_config(namespace, config)

    def get_configuration(self, tag: str | Tag, overrides: ConfigurationType | None = None) -> ConfigurationType | dict:
        if isinstance(tag, str):
            tag = Tag.from_string(tag)
        base = self.configurations.get(tag)
        if not base and overrides is None:
            raise KeyError(f"{tag} does not have a registered configuration")
        elif not base:
            return overrides
        config = create_config(base._namespace, base.to_dict(private=True, protected=True))
        if overrides:
            config.update(overrides.to_dict(protected=True))
        return config

    #####################
    # Processors
    #####################

    def register_processor(self, tag: str | Tag, processor: ProcessorProtocol,
                           config: ConfigurationType | dict | None = None) -> Tag:
        if isinstance(tag, str):
            tag = Tag.from_string(tag)
        if tag.category != "processor":
            raise ValueError(f"Expected a tag with 'processor' category but found '{tag.category}'")
        self.register_class(tag, processor)
        namespace = processor.config._namespace
        config = self._normalize_config(namespace, config)
        if config:
            self.configurations[tag] = config
        return tag

    def unregister_processor(self, tag: str | Tag) -> None:
        if isinstance(tag, str):
            tag = Tag.from_string(tag)
        if tag.category != "processor":
            raise ValueError(f"Expected a tag with 'processor' category but found '{tag.category}'")
        del self.classes[tag]
        self.configurations.pop(tag, None)

    def get_processor(self, tag: str | Tag, overrides: ConfigurationType | dict | None = None) -> ProcessorProtocol:
        if isinstance(tag, str):
            tag = Tag.from_string(tag)
        if tag.category != "processor":
            raise ValueError(f"Expected a tag with 'processor' category but found '{tag.category}'")
        processor = cast(ProcessorProtocol, _import_class(self.classes[tag]))
        namespace = processor.config._namespace
        overrides = self._normalize_config(namespace, overrides) or {}
        config = self.get_configuration(tag, overrides)
        return processor(config=config)

    #####################
    # Resources
    #####################

    @staticmethod
    def _get_resource_namespace(resource: type[ResourceProtocol]) -> list[str]:
        legacy_namespace = getattr(resource, "CONFIG_NAMESPACE", None)
        namespace = getattr(resource, "NAMESPACE", legacy_namespace)
        if namespace is None:
            raise ValueError("Can't register Resources that do not specify either NAMESPACE or CONFIG_NAMESPACE")
        elif isinstance(namespace, str):
            namespace = [namespace]
        return namespace

    def register_resource(self, tag: str | Tag, resource: type[ResourceProtocol],
                          config: ConfigurationType | dict | None = None) -> Tag:
        if isinstance(tag, str):
            tag = Tag.from_string(tag)
        if tag.category != "resource":
            raise ValueError(f"Expected a tag with 'resource' category but found '{tag.category}'")
        self.register_class(tag, resource)
        namespace = self._get_resource_namespace(resource)
        config = self._normalize_config(namespace, config)
        if config:
            self.configurations[tag] = config
        return tag

    def unregister_resource(self, tag: str | Tag) -> None:
        if isinstance(tag, str):
            tag = Tag.from_string(tag)
        if tag.category != "resource":
            raise ValueError(f"Expected a tag with 'resource' category but found '{tag.category}'")
        del self.classes[tag]
        self.configurations.pop(tag, None)

    def get_resource(self, tag: str | Tag, overrides: ConfigurationType | dict | None = None) -> ResourceProtocol:
        if isinstance(tag, str):
            tag = Tag.from_string(tag)
        if tag.category != "resource":
            raise ValueError(f"Expected a tag with 'resource' category but found '{tag.category}'")
        resource = cast(ResourceProtocol, _import_class(self.classes[tag]))
        namespace = self._get_resource_namespace(resource)
        overrides = self._normalize_config(namespace, overrides) or {}
        config = self.get_configuration(tag, overrides)
        return resource(config=config)
