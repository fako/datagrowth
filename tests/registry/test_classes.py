import pytest

from datagrowth.registry import Registry, Tag


class TestClass:
    pass


@pytest.fixture
def registry() -> Registry:
    return Registry()


def test_register_class_stores_import_path(registry: Registry) -> None:
    tag = registry.register_class("test:class", TestClass)
    assert tag == Tag.from_string("test:class")
    assert registry.classes[tag] == f"{TestClass.__module__}.{TestClass.__qualname__}"


def test_unregister_class_with_string_tag(registry: Registry) -> None:
    registry.register_class("test:class", TestClass)
    registry.unregister_class("test:class")
    assert Tag.from_string("test:class") not in registry.classes


def test_get_class_reports_import_path_error_message(registry: Registry) -> None:
    tag = registry.register_class("test:class", TestClass)
    faulty_path = "datagrowth.registry.does_not_exist.DoesNotExist"
    registry.classes[tag] = faulty_path

    with pytest.raises(AttributeError, match="has no attribute 'does_not_exist'"):
        registry.get_class(tag)


def test_get_class_reports_completely_invalid_path(registry: Registry) -> None:
    tag = registry.register_class("test:class", TestClass)
    faulty_path = "not_a_real_module.or_class"
    registry.classes[tag] = faulty_path

    with pytest.raises(ImportError, match=f"Could not import class path '{faulty_path}'"):
        registry.get_class(tag)


def test_get_class_reports_type_mismatch(registry: Registry) -> None:
    tag = registry.register_class("test:class", TestClass)
    faulty_path = "datagrowth.registry.types._import_class"
    registry.classes[tag] = faulty_path

    with pytest.raises(TypeError, match="Expected class import from path"):
        registry.get_class(tag)
