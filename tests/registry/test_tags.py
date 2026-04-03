import pytest

from datagrowth.registry import Registry, Tag


@pytest.fixture
def registry() -> Registry:
    tags = Tag.from_strings("test:value", "test:default", "default:value")
    return Registry.from_tags(tags)


def test_register_tag(registry: Registry) -> None:
    # Register with a string
    tag: Tag = registry.register_tag("new:value")
    assert "new:value" in registry.tags
    assert len(registry.tags) == 4
    assert isinstance(tag, Tag)
    assert registry.tags["new:value"] == tag
    # Register with a tag
    tag = Tag(category="new", value="default")
    registry.register_tag(tag)
    assert "new:default" in registry.tags
    assert len(registry.tags) == 5
    assert registry.tags["new:default"] == tag


def test_unregister_tag(registry: Registry) -> None:
    # Unregister with a string
    registry.unregister_tag("test:default")
    assert "test:default" not in registry.tags
    assert len(registry.tags) == 2
    # Unregister with a tag
    tag = Tag(category="test", value="value")
    registry.unregister_tag(tag)
    assert "test:value" not in registry.tags
    assert len(registry.tags) == 1


def test_tag_from_string_lowercase() -> None:
    tag = Tag.from_string("Test:Value")
    assert tag.category == "test"
    assert tag.value == "value"
    tag = Tag.from_string("TEST:VALUE")
    assert tag.category == "test"
    assert tag.value == "value"
    assert str(tag) == "test:value"


def test_tags_by_category(registry: Registry) -> None:
    test_tags = registry.tags_by_category("test")
    assert test_tags == [
        Tag.from_string("test:value"),
        Tag.from_string("test:default"),
    ]
    default_tags = registry.tags_by_category("default")
    assert default_tags == [
        Tag.from_string("default:value"),
    ]


def test_clear_category() -> None:
    tags = Tag.from_strings("fruit:apple", "fruit:banana", "color:red", "color:blue")
    registry = Registry.from_tags(tags)
    registry.clear_category("fruit")
    assert registry.tags_by_category("fruit") == []
    assert "fruit:apple" not in registry.tags
    assert "fruit:banana" not in registry.tags
    assert "color:red" in registry.tags
    assert "color:blue" in registry.tags


def test_tags_by_value(registry: Registry) -> None:
    test_tags = registry.tags_by_value("value")
    assert test_tags == [
        Tag.from_string("test:value"),
        Tag.from_string("default:value"),

    ]
    default_tags = registry.tags_by_value("default")
    assert default_tags == [
        Tag.from_string("test:default"),
    ]
