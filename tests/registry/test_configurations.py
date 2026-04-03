import pytest

from datagrowth.configuration import ConfigurationType, create_config
from datagrowth.registry import Registry, Tag


@pytest.fixture
def registry() -> Registry:
    return Registry()


def test_get_configuration_raises_when_nothing_registered(registry: Registry) -> None:
    with pytest.raises(KeyError):
        registry.get_configuration("test:value")


def test_get_configuration_raises_with_tag_object(registry: Registry) -> None:
    tag = Tag(category="test", value="value")
    with pytest.raises(KeyError):
        registry.get_configuration(tag)


def test_get_configuration_returns_overrides_when_no_base(registry: Registry) -> None:
    overrides = create_config("test", {"batch_size": 99})
    result = registry.get_configuration("test:value", overrides)
    assert result is overrides


def test_get_configuration_returns_base_when_no_overrides(registry: Registry) -> None:
    tag = Tag(category="test", value="value")
    base = create_config("test", {"batch_size": 99})
    registry.configurations[tag] = base
    result = registry.get_configuration(tag)
    assert isinstance(result, ConfigurationType)
    assert result.batch_size == 99


def test_get_configuration_base_is_not_mutated(registry: Registry) -> None:
    tag = Tag(category="test", value="value")
    base = create_config("test", {"batch_size": 99})
    registry.configurations[tag] = base
    overrides = create_config("test", {"batch_size": 50})
    result = registry.get_configuration(tag, overrides)
    assert result.batch_size == 50
    assert base.batch_size == 99


def test_get_configuration_merges_base_and_overrides(registry: Registry) -> None:
    tag = Tag(category="test", value="value")
    base = create_config("test", {"batch_size": 99, "sample_size": 10})
    registry.configurations[tag] = base
    overrides = create_config("test", {"batch_size": 50})
    result = registry.get_configuration(tag, overrides)
    assert result.batch_size == 50
    assert result.sample_size == 10
