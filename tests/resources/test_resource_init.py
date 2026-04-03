from datagrowth.configuration import ConfigurationProperty, ConfigurationType
from datagrowth.registry import DATAGROWTH_REGISTRY, Tag
from datagrowth.resources.pydantic import Resource
from datagrowth.signatures import Signature
from unittest.mock import patch


class MockStorage:

    config = ConfigurationProperty(namespace="mock_storage")

    def __init__(self, config: ConfigurationType | dict) -> None:
        self.config = config

    def save(self, resource: Resource) -> None:
        return None

    def load(self, signature: Signature) -> Resource | None:
        return None


class MockExtractor:

    config = ConfigurationProperty(namespace="mock_extractor")

    def __init__(self, config: ConfigurationType | dict) -> None:
        self.config = config

    def extract(self, signature: Signature) -> Resource:
        return Resource(signature=signature)


class MockResource(Resource):
    STORAGE = Tag(category="storage", value="mock-resource-config")
    EXTRACTOR = Tag(category="extractor", value="mock-resource-config")


def test_resource_without_storage_or_extractor_tag_keeps_none() -> None:
    resource = Resource()
    assert resource.storage is None
    assert resource.extractor is None


def test_resource_post_init_resolves_storage_and_extractor_from_registry() -> None:
    with (
        patch.object(DATAGROWTH_REGISTRY, "get_storage", return_value=MockStorage(config={})) as get_storage,
        patch.object(DATAGROWTH_REGISTRY, "get_extractor", return_value=MockExtractor(config={})) as get_extractor,
    ):
        resource = MockResource()
        assert isinstance(resource.storage, MockStorage)
        assert isinstance(resource.extractor, MockExtractor)
        get_storage.assert_called_once_with(MockResource.STORAGE)
        get_extractor.assert_called_once_with(MockResource.EXTRACTOR)
