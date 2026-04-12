import pytest

from datagrowth.configuration import ConfigurationType, create_config, ConfigurationProperty
from datagrowth.registry import Registry, Tag
from datagrowth.resources.protocols import ResourceProtocol
from datagrowth.signatures import Signature

from registry.mock_resource import MockResource


class MockExtractor:
    config = ConfigurationProperty(namespace="http_resource")

    def __init__(self, config: ConfigurationType) -> None:
        self.config = config

    def extract(self, signature: Signature) -> ResourceProtocol:
        return MockResource()


@pytest.fixture
def registry() -> Registry:
    return Registry()


def test_register_extractor_with_string_tag(registry: Registry) -> None:
    tag = registry.register_extractor("extractor:test", MockExtractor)
    assert isinstance(tag, Tag)
    assert tag == Tag.from_string("extractor:test")
    assert "extractor:test" in registry.tags
    assert tag in registry.classes
    assert registry.classes[tag] == f"{MockExtractor.__module__}.{MockExtractor.__qualname__}"


def test_register_extractor_with_tag_object(registry: Registry) -> None:
    tag_input = Tag(category="extractor", value="test")
    tag = registry.register_extractor(tag_input, MockExtractor, None)
    assert tag == tag_input
    assert "extractor:test" in registry.tags
    assert tag in registry.classes


def test_register_extractor_with_dict_config(registry: Registry) -> None:
    tag = registry.register_extractor("extractor:test", MockExtractor, {"continuation_limit": 99})
    assert tag in registry.configurations
    stored = registry.configurations[tag]
    assert isinstance(stored, ConfigurationType)
    assert stored.continuation_limit == 99


def test_register_extractor_with_configuration_type(registry: Registry) -> None:
    config = create_config("mock_extractor", {"continuation_limit": 99})
    tag = registry.register_extractor("extractor:test", MockExtractor, config)
    assert tag in registry.configurations
    assert registry.configurations[tag].continuation_limit == 99


def test_register_extractor_without_config_stores_no_configuration(registry: Registry) -> None:
    tag = registry.register_extractor("extractor:test", MockExtractor, None)
    assert tag not in registry.configurations


def test_unregister_extractor_with_string_tag(registry: Registry) -> None:
    tag = registry.register_extractor("extractor:test", MockExtractor)
    registry.unregister_extractor("extractor:test")
    assert tag not in registry.classes
    assert tag not in registry.configurations


def test_unregister_extractor_with_tag_object(registry: Registry) -> None:
    tag = registry.register_extractor("extractor:test", MockExtractor)
    registry.unregister_extractor(tag)
    assert tag not in registry.classes
    assert tag not in registry.configurations


def test_get_extractor_returns_instance(registry: Registry) -> None:
    registry.register_extractor("extractor:test", MockExtractor, {"continuation_limit": 99})
    extractor = registry.get_extractor("extractor:test")
    assert isinstance(extractor, MockExtractor)
    assert extractor.config.continuation_limit == 99


def test_get_extractor_applies_overrides(registry: Registry) -> None:
    registry.register_extractor("extractor:test", MockExtractor)
    extractor = registry.get_extractor("extractor:test", {"continuation_limit": 99})
    assert isinstance(extractor, MockExtractor)
    assert extractor.config.continuation_limit == 99


def test_get_extractor_with_only_overrides(registry: Registry) -> None:
    registry.register_extractor("extractor:test", MockExtractor)
    extractor = registry.get_extractor("extractor:test", {"continuation_limit": 99})
    assert isinstance(extractor, MockExtractor)
    assert extractor.config.continuation_limit == 99


def test_get_extractor_without_any_config(registry: Registry) -> None:
    registry.register_extractor("extractor:test", MockExtractor)
    extractor = registry.get_extractor("extractor:test")
    assert isinstance(extractor, MockExtractor)
    assert extractor.config.continuation_limit == 1


def test_get_extractor_with_tag_object(registry: Registry) -> None:
    tag = Tag(category="extractor", value="test")
    registry.register_extractor(tag, MockExtractor, {"continuation_limit": 99})
    extractor = registry.get_extractor(tag)
    assert isinstance(extractor, MockExtractor)
    assert extractor.config.continuation_limit == 99


def test_extractor_methods_raise_for_wrong_category(registry: Registry) -> None:
    expected = "Expected a tag with 'extractor' category but found 'wrong'"
    with pytest.raises(ValueError, match=expected):
        registry.register_extractor("wrong:test", MockExtractor)
    with pytest.raises(ValueError, match=expected):
        registry.unregister_extractor("wrong:test")
    with pytest.raises(ValueError, match=expected):
        registry.get_extractor("wrong:test")
