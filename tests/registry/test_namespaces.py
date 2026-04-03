import pytest

from datagrowth.registry import Registry, Tag


@pytest.fixture
def registry() -> Registry:
    return Registry()


def test_register_namespace_with_string(registry: Registry) -> None:
    tag = registry.register_namespace("namespace:test")
    assert isinstance(tag, Tag)
    assert tag == Tag.from_string("namespace:test")
    assert tag in registry.namespaces
    assert "namespace:test" in registry.tags


def test_register_namespace_with_tag_object(registry: Registry) -> None:
    tag_input = Tag(category="namespace", value="test")
    tag = registry.register_namespace(tag_input)
    assert tag == tag_input
    assert tag in registry.namespaces
    assert "namespace:test" in registry.tags


def test_register_namespace_rejects_wrong_category(registry: Registry) -> None:
    with pytest.raises(ValueError, match="Expected a tag with 'namespace' category"):
        registry.register_namespace("processor:test")


def test_register_namespace_rejects_wrong_category_tag_object(registry: Registry) -> None:
    tag = Tag(category="resource", value="test")
    with pytest.raises(ValueError, match="Expected a tag with 'namespace' category"):
        registry.register_namespace(tag)


def test_unregister_namespace_with_string(registry: Registry) -> None:
    registry.register_namespace("namespace:test")
    registry.unregister_namespace("namespace:test")
    assert Tag.from_string("namespace:test") not in registry.namespaces
    assert "namespace:test" not in registry.tags


def test_unregister_namespace_with_tag_object(registry: Registry) -> None:
    tag = registry.register_namespace("namespace:test")
    registry.unregister_namespace(tag)
    assert tag not in registry.namespaces
    assert "namespace:test" not in registry.tags


def test_unregister_namespace_rejects_wrong_category(registry: Registry) -> None:
    with pytest.raises(ValueError, match="Expected a tag with 'namespace' category"):
        registry.unregister_namespace("processor:test")


def test_get_namespace(registry: Registry) -> None:
    registry.register_namespace("namespace:test")
    tag = registry.get_namespace("namespace:test")
    assert isinstance(tag, Tag)
    assert tag == Tag.from_string("namespace:test")


def test_get_namespace_raises_when_not_registered(registry: Registry) -> None:
    with pytest.raises(KeyError, match="not registered as a namespace"):
        registry.get_namespace("namespace:missing")
