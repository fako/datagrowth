from pathlib import Path

import pytest

from datagrowth.registry import Registry, Tag


@pytest.fixture
def registry() -> Registry:
    return Registry()


def test_register_directory_with_string_tag_and_string_path(registry: Registry) -> None:
    tag = registry.register_directory("directory:data", "/tmp/data")
    assert isinstance(tag, Tag)
    assert tag == Tag.from_string("directory:data")
    assert "directory:data" in registry.tags
    assert registry.directories[tag] == Path("/tmp/data")


def test_register_directory_with_tag_object_and_path(registry: Registry) -> None:
    tag = Tag(category="directory", value="data")
    path = Path("/tmp/data")
    returned = registry.register_directory(tag, path)
    assert returned == tag
    assert returned in registry.directories
    assert registry.directories[returned] == path


def test_unregister_directory_with_string_tag(registry: Registry) -> None:
    tag = registry.register_directory("directory:data", "/tmp/data")
    registry.unregister_directory("directory:data")
    assert tag not in registry.directories
    assert "directory:data" not in registry.tags


def test_unregister_directory_with_tag_object(registry: Registry) -> None:
    tag = registry.register_directory("directory:data", "/tmp/data")
    registry.unregister_directory(tag)
    assert tag not in registry.directories
    assert "directory:data" not in registry.tags


def test_get_directory_with_string_tag(registry: Registry) -> None:
    registry.register_directory("directory:data", "/tmp/data")
    directory = registry.get_directory("directory:data")
    assert directory == Path("/tmp/data")


def test_get_directory_with_tag_object(registry: Registry) -> None:
    tag = registry.register_directory("directory:data", "/tmp/data")
    directory = registry.get_directory(tag)
    assert directory == Path("/tmp/data")


def test_get_directory_raises_when_not_registered(registry: Registry) -> None:
    with pytest.raises(KeyError):
        registry.get_directory("directory:missing")
