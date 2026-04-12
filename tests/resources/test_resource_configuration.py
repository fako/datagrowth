import pytest

from datagrowth.configuration import ConfigurationType
from datagrowth.registry import Tag
from datagrowth.resources.pydantic import Resource


@pytest.fixture
def mock_resource_class() -> type[Resource]:
    class ParentMockResource(Resource):
        NAMESPACE = Tag(category="namespace", value="parent_resource")

    class MockResource(ParentMockResource):
        NAMESPACE = Tag(category="namespace", value="mock_resource")

    return MockResource


def test_resource_config_accepts_dict() -> None:
    resource = Resource(config={"timeout": 10, "cache_only": True})  # type: ignore[reportArgumentType]
    assert isinstance(resource.config, ConfigurationType)
    assert resource.config.timeout == 10
    assert resource.config.cache_only is True


def test_resource_config_accepts_configuration_type() -> None:
    config = ConfigurationType(namespace="resource")
    config.update({"retries": 3})
    resource = Resource(config=config)
    assert resource.config is config
    assert resource.config.retries == 3


def test_resource_config_defaults_to_configuration_type() -> None:
    resource = Resource()
    assert isinstance(resource.config, ConfigurationType)


def test_resource_config_rejects_invalid_type() -> None:
    with pytest.raises(TypeError, match="Resource config expects a dict, ConfigurationType or None"):
        Resource(config=123)  # type: ignore[reportArgumentType]


def test_resource_dump_serializes_public_config_only_by_default() -> None:
    config = {"public": "value", "_secret": "hidden", "_private": ["_secret"]}
    resource = Resource(config=config)  # type: ignore[reportArgumentType]
    dumped = resource.model_dump()
    assert dumped["config"] == {"public": "value"}


def test_resource_dump_can_include_protected_and_private_config() -> None:
    config = {"public": "value", "_secret": "hidden", "_private": ["_secret"]}
    resource = Resource(config=config)  # type: ignore[reportArgumentType]
    dumped = resource.model_dump(context={"config_protected": True, "config_private": True})
    assert dumped["config"]["public"] == "value"
    assert dumped["config"]["_secret"] == "hidden"
    assert "_private" in dumped["config"]


def test_resource_namespace_resolution_from_inheritance_chain(mock_resource_class: type[Resource]) -> None:
    assert mock_resource_class._get_config_namespaces() == [
        "mock_resource",
        "parent_resource",
        "resource",
    ]

    resource = mock_resource_class()
    assert isinstance(resource.config, ConfigurationType)
    assert resource.config._namespace == ["mock_resource", "parent_resource", "resource"]


def test_resource_namespace_prefers_mock_override_over_parent(mock_resource_class: type[Resource]) -> None:
    config = ConfigurationType(
        defaults={
            "mock_resource_override": "mock",
            "parent_resource_override": "parent",
        },
        namespace=mock_resource_class._get_config_namespaces(),
    )
    resource = mock_resource_class(config=config)
    assert resource.config.override == "mock"
