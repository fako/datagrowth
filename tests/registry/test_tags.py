import pytest

from datagrowth.registry.types import TagRegistry, Tag


@pytest.fixture
def tag_registry() -> TagRegistry:
    tags = Tag.from_strings("test:value", "test:default", "default:value")
    return TagRegistry.from_tags(tags)


def test_register_tag(tag_registry: TagRegistry) -> None:
    # Register with a string
    tag: Tag = tag_registry.register("new:value")
    assert "new:value" in tag_registry.tags
    assert len(tag_registry.tags) == 4
    assert isinstance(tag, Tag)
    assert tag_registry.tags["new:value"] == tag
    # Register with a tag
    tag = Tag(category="new", value="default")
    tag_registry.register(tag)
    assert "new:default" in tag_registry.tags
    assert len(tag_registry.tags) == 5
    assert tag_registry.tags["new:default"] == tag


def test_unregister_tag(tag_registry: TagRegistry) -> None:
    # Unregister with a string
    tag_registry.unregister("test:default")
    assert "test:default" not in tag_registry.tags
    assert len(tag_registry.tags) == 2
    # Unregister with a tag
    tag = Tag(category="test", value="value")
    tag_registry.unregister(tag)
    assert "test:value" not in tag_registry.tags
    assert len(tag_registry.tags) == 1


def test_tags_by_category(tag_registry: TagRegistry) -> None:
    test_tags = tag_registry.tags_by_category("test")
    assert test_tags == [
        Tag.from_string("test:value"),
        Tag.from_string("test:default"),
    ]
    default_tags = tag_registry.tags_by_category("default")
    assert default_tags == [
        Tag.from_string("default:value"),
    ]


def test_tags_by_value(tag_registry: TagRegistry) -> None:
    test_tags = tag_registry.tags_by_value("value")
    assert test_tags == [
        Tag.from_string("test:value"),
        Tag.from_string("default:value"),

    ]
    default_tags = tag_registry.tags_by_value("default")
    assert default_tags == [
        Tag.from_string("test:default"),
    ]
