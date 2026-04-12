from pathlib import Path
import pytest

from datagrowth.configuration import ConfigurationProperty, ConfigurationType, create_config
from datagrowth.registry import Registry, Tag
from datagrowth.resources.protocols import ResourceProtocol
from datagrowth.signatures import Signature


class MockStorage:
    config = ConfigurationProperty(namespace="mock_storage")

    def __init__(self, config: ConfigurationType) -> None:
        self.config = config

    def save(self, resource: ResourceProtocol) -> Signature:
        return Signature(uri="mock://")

    def load(self, signature: Signature) -> ResourceProtocol | None:
        return None

    def read(self, signature: Signature, filename: str) -> bytes | str:
        return b""

    def write(self, signature: Signature, filename: str, data: bytes | str) -> Path:
        return Path(filename)

    def read_tmp(self, filename: str) -> bytes | str:
        return b""

    def write_tmp(self, filename: str, data: bytes | str) -> Path:
        return Path(filename)


@pytest.fixture
def registry() -> Registry:
    return Registry()


def test_register_storage_with_string_tag(registry: Registry) -> None:
    tag = registry.register_storage("storage:test", MockStorage)
    assert isinstance(tag, Tag)
    assert tag == Tag.from_string("storage:test")
    assert "storage:test" in registry.tags
    assert tag in registry.classes
    assert registry.classes[tag] == f"{MockStorage.__module__}.{MockStorage.__qualname__}"


def test_register_storage_with_tag_object(registry: Registry) -> None:
    tag_input = Tag(category="storage", value="test")
    tag = registry.register_storage(tag_input, MockStorage, None)
    assert tag == tag_input
    assert "storage:test" in registry.tags
    assert tag in registry.classes


def test_register_storage_with_dict_config(registry: Registry) -> None:
    tag = registry.register_storage("storage:test", MockStorage, {"batch_size": 99})
    assert tag in registry.configurations
    stored = registry.configurations[tag]
    assert stored.batch_size == 99


def test_register_storage_with_configuration_type(registry: Registry) -> None:
    config = create_config("mock_storage", {"batch_size": 99})
    tag = registry.register_storage("storage:test", MockStorage, config)
    assert tag in registry.configurations
    assert registry.configurations[tag].batch_size == 99


def test_register_storage_without_config_stores_no_configuration(registry: Registry) -> None:
    tag = registry.register_storage("storage:test", MockStorage, None)
    assert tag not in registry.configurations


def test_unregister_storage_with_string_tag(registry: Registry) -> None:
    tag = registry.register_storage("storage:test", MockStorage)
    registry.unregister_storage("storage:test")
    assert tag not in registry.classes
    assert tag not in registry.configurations


def test_unregister_storage_with_tag_object(registry: Registry) -> None:
    tag = registry.register_storage("storage:test", MockStorage)
    registry.unregister_storage(tag)
    assert tag not in registry.classes
    assert tag not in registry.configurations


def test_get_storage_returns_instance(registry: Registry) -> None:
    registry.register_storage("storage:test", MockStorage, {"batch_size": 99})
    storage = registry.get_storage("storage:test")
    assert isinstance(storage, MockStorage)
    assert storage.config.batch_size == 99


def test_get_storage_applies_overrides(registry: Registry) -> None:
    registry.register_storage("storage:test", MockStorage)
    storage = registry.get_storage("storage:test", {"batch_size": 99})
    assert isinstance(storage, MockStorage)
    assert storage.config.batch_size == 99


def test_get_storage_with_only_overrides(registry: Registry) -> None:
    registry.register_storage("storage:test", MockStorage)
    storage = registry.get_storage("storage:test", {"batch_size": 99})
    assert isinstance(storage, MockStorage)
    assert storage.config.batch_size == 99


def test_get_storage_without_any_config(registry: Registry) -> None:
    registry.register_storage("storage:test", MockStorage)
    storage = registry.get_storage("storage:test")
    assert isinstance(storage, MockStorage)
    assert storage.config.batch_size == 100


def test_get_storage_with_tag_object(registry: Registry) -> None:
    tag = Tag(category="storage", value="test")
    registry.register_storage(tag, MockStorage, {"batch_size": 99})
    storage = registry.get_storage(tag)
    assert isinstance(storage, MockStorage)
    assert storage.config.batch_size == 99


def test_storage_methods_raise_for_wrong_category(registry: Registry) -> None:
    expected = "Expected a tag with 'storage' category but found 'wrong'"
    with pytest.raises(ValueError, match=expected):
        registry.register_storage("wrong:test", MockStorage)
    with pytest.raises(ValueError, match=expected):
        registry.unregister_storage("wrong:test")
    with pytest.raises(ValueError, match=expected):
        registry.get_storage("wrong:test")
