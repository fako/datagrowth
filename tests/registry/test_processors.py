import pytest

from datagrowth.configuration import ConfigurationProperty, ConfigurationType, create_config
from datagrowth.registry import Registry, Tag


class MockProcessor:
    """
    A minimal processor satisfying ProcessorProtocol for testing.

    Due to legacy reasons a Processor.config needs an empty dict to indicate there is no config.
    A value of None is not allowed.
    """
    config = ConfigurationProperty(namespace="mock")

    def __init__(self, config: ConfigurationType | dict) -> None:
        self.config = config


@pytest.fixture
def registry() -> Registry:
    return Registry()


def test_register_processor_with_string_tag(registry: Registry) -> None:
    tag = registry.register_processor("processor:test", MockProcessor)
    assert isinstance(tag, Tag)
    assert tag == Tag.from_string("processor:test")
    assert "processor:test" in registry.tags
    assert tag in registry.classes
    assert registry.classes[tag] == f"{MockProcessor.__module__}.{MockProcessor.__qualname__}"


def test_register_processor_with_tag_object(registry: Registry) -> None:
    tag_input = Tag(category="processor", value="test")
    tag = registry.register_processor(tag_input, MockProcessor, None)
    assert tag == tag_input
    assert "processor:test" in registry.tags
    assert tag in registry.classes


def test_register_processor_with_dict_config(registry: Registry) -> None:
    tag = registry.register_processor("processor:test", MockProcessor, {"batch_size": 99})
    assert tag in registry.configurations
    stored = registry.configurations[tag]
    assert isinstance(stored, ConfigurationType)
    assert stored.batch_size == 99


def test_register_processor_with_configuration_type(registry: Registry) -> None:
    config = create_config("mock", {"batch_size": 99})
    tag = registry.register_processor("processor:test", MockProcessor, config)
    assert tag in registry.configurations
    assert registry.configurations[tag].batch_size == 99


def test_register_processor_without_config_stores_no_configuration(registry: Registry) -> None:
    tag = registry.register_processor("processor:test", MockProcessor, None)
    assert tag not in registry.configurations


def test_unregister_processor_with_string_tag(registry: Registry) -> None:
    tag = registry.register_processor("processor:test", MockProcessor)
    registry.unregister_processor("processor:test")
    assert tag not in registry.classes
    assert tag not in registry.configurations


def test_unregister_processor_with_tag_object(registry: Registry) -> None:
    tag = registry.register_processor("processor:test", MockProcessor)
    registry.unregister_processor(tag)
    assert tag not in registry.classes
    assert tag not in registry.configurations


def test_get_processor_returns_instance(registry: Registry) -> None:
    registry.register_processor("processor:test", MockProcessor, {"batch_size": 99})
    processor = registry.get_processor("processor:test")
    assert isinstance(processor, MockProcessor)
    assert processor.config.batch_size == 99


def test_get_processor_applies_overrides(registry: Registry) -> None:
    registry.register_processor("processor:test", MockProcessor)
    processor = registry.get_processor("processor:test", {"batch_size": 99})
    assert isinstance(processor, MockProcessor)
    assert processor.config.batch_size == 99


def test_get_processor_with_only_overrides(registry: Registry) -> None:
    registry.register_processor("processor:test", MockProcessor)
    processor = registry.get_processor("processor:test", {"batch_size": 99})
    assert isinstance(processor, MockProcessor)
    assert processor.config.batch_size == 99


def test_get_processor_without_any_config(registry: Registry) -> None:
    registry.register_processor("processor:test", MockProcessor)
    processor = registry.get_processor("processor:test")
    assert isinstance(processor, MockProcessor)
    assert processor.config.batch_size == 100


def test_get_processor_with_tag_object(registry: Registry) -> None:
    tag = Tag(category="processor", value="test")
    registry.register_processor(tag, MockProcessor, {"batch_size": 99})
    processor = registry.get_processor(tag)
    assert isinstance(processor, MockProcessor)
    assert processor.config.batch_size == 99


def test_processor_methods_raise_for_wrong_category(registry: Registry) -> None:
    expected = "Expected a tag with 'processor' category but found 'wrong'"
    with pytest.raises(ValueError, match=expected):
        registry.register_processor("wrong:test", MockProcessor)
    with pytest.raises(ValueError, match=expected):
        registry.unregister_processor("wrong:test")
    with pytest.raises(ValueError, match=expected):
        registry.get_processor("wrong:test")
