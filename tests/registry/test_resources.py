import pytest

from datagrowth.configuration import ConfigurationType, create_config
from datagrowth.registry import Registry, Tag


class MockResource:
    NAMESPACE = "mock_resource"

    def __init__(self, config: ConfigurationType | dict | None = None) -> None:
        if config is None:
            self.config = create_config("mock_resource", {})
        elif isinstance(config, dict):
            self.config = create_config("mock_resource", config)
        else:
            self.config = config

    def close(self) -> "MockResource":
        return self

    @classmethod
    def get_name(cls) -> str:
        return cls.__name__.lower()

    def extract(self, *args, **kwargs) -> "MockResource":
        return self

    @property
    def success(self) -> bool:
        return True

    @property
    def content(self) -> tuple[str, dict]:
        return "application/json", {}

    def handle_errors(self) -> None:
        return None


@pytest.fixture
def registry() -> Registry:
    return Registry()


def test_register_resource_with_string_tag(registry: Registry) -> None:
    tag = registry.register_resource("resource:test", MockResource)
    assert isinstance(tag, Tag)
    assert tag == Tag.from_string("resource:test")
    assert "resource:test" in registry.tags
    assert tag in registry.classes
    assert registry.classes[tag] == f"{MockResource.__module__}.{MockResource.__qualname__}"


def test_register_resource_with_tag_object(registry: Registry) -> None:
    tag_input = Tag(category="resource", value="test")
    tag = registry.register_resource(tag_input, MockResource, None)
    assert tag == tag_input
    assert "resource:test" in registry.tags
    assert tag in registry.classes


def test_register_resource_with_dict_config(registry: Registry) -> None:
    tag = registry.register_resource("resource:test", MockResource, {"batch_size": 99})
    assert tag in registry.configurations
    stored = registry.configurations[tag]
    assert isinstance(stored, ConfigurationType)
    assert stored.batch_size == 99


def test_register_resource_with_configuration_type(registry: Registry) -> None:
    config = create_config("mock_resource", {"batch_size": 99})
    tag = registry.register_resource("resource:test", MockResource, config)
    assert tag in registry.configurations
    assert registry.configurations[tag].batch_size == 99


def test_register_resource_without_config_stores_no_configuration(registry: Registry) -> None:
    tag = registry.register_resource("resource:test", MockResource, None)
    assert tag not in registry.configurations


def test_unregister_resource_with_string_tag(registry: Registry) -> None:
    tag = registry.register_resource("resource:test", MockResource)
    registry.unregister_resource("resource:test")
    assert tag not in registry.classes
    assert tag not in registry.configurations


def test_unregister_resource_with_tag_object(registry: Registry) -> None:
    tag = registry.register_resource("resource:test", MockResource)
    registry.unregister_resource(tag)
    assert tag not in registry.classes
    assert tag not in registry.configurations


def test_get_resource_returns_instance(registry: Registry) -> None:
    registry.register_resource("resource:test", MockResource, {"batch_size": 99})
    resource = registry.get_resource("resource:test")
    assert isinstance(resource, MockResource)
    assert resource.config.batch_size == 99


def test_get_resource_applies_overrides(registry: Registry) -> None:
    registry.register_resource("resource:test", MockResource)
    resource = registry.get_resource("resource:test", {"batch_size": 99})
    assert isinstance(resource, MockResource)
    assert resource.config.batch_size == 99


def test_get_resource_with_tag_object(registry: Registry) -> None:
    tag = Tag(category="resource", value="test")
    registry.register_resource(tag, MockResource, {"batch_size": 99})
    resource = registry.get_resource(tag)
    assert isinstance(resource, MockResource)
    assert resource.config.batch_size == 99


def test_resource_methods_raise_for_wrong_category(registry: Registry) -> None:
    expected = "Expected a tag with 'resource' category but found 'wrong'"
    with pytest.raises(ValueError, match=expected):
        registry.register_resource("wrong:test", MockResource)
    with pytest.raises(ValueError, match=expected):
        registry.unregister_resource("wrong:test")
    with pytest.raises(ValueError, match=expected):
        registry.get_resource("wrong:test")
