from django.test import TestCase
from django.apps import apps

from datagrowth.registry import Registry
from datagrowth.registry import DATAGROWTH_REGISTRY
from resources.models import (
    EntityDetailResource,
    EntityIdListResource,
    EntityListResource,
    HttpImageResourceMock,
    HttpResourceMock,
    MicroServiceResourceMock,
    ShellResourceMock,
    URLResourceMock,
)
from vendors.models import MockTikaResource


class TestDatagrowthResourceDjangoConfig(TestCase):

    def setUp(self):
        super().setUp()
        self.config = apps.get_app_config("datagrowth")
        self.expected_resources = {
            "resources.httpresourcemock": HttpResourceMock,
            "resources.urlresourcemock": URLResourceMock,
            "resources.httpimageresourcemock": HttpImageResourceMock,
            "resources.microserviceresourcemock": MicroServiceResourceMock,
            "resources.shellresourcemock": ShellResourceMock,
            "resources.entitylistresource": EntityListResource,
            "resources.entityidlistresource": EntityIdListResource,
            "resources.entitydetailresource": EntityDetailResource,
            "vendors.mocktikaresource": MockTikaResource,
        }

    def test_load_resources(self):
        self.config.load_resources()
        resource_tags = DATAGROWTH_REGISTRY.tags_by_category("resource")
        self.assertEqual(len(resource_tags), len(self.expected_resources))
        for tag_value, expected_class in self.expected_resources.items():
            self.assertEqual(DATAGROWTH_REGISTRY.get_class(f"resource:{tag_value}"), expected_class)


class TestResourceRegistry(TestCase):

    def setUp(self) -> None:
        super().setUp()
        self.registry = Registry()

    def test_register_http_resource_mock_uses_global_defaults(self) -> None:
        tag = self.registry.register_resource("resource:HttpResourceMock", HttpResourceMock)

        self.assertIn("resource:httpresourcemock", self.registry.tags)
        self.assertIn(tag, self.registry.classes)

        resource = self.registry.get_resource(tag)
        self.assertIsInstance(resource, HttpResourceMock)
        self.assertEqual(resource.config.source_language, "en")

    def test_get_resource_overrides_global_defaults(self) -> None:
        tag = self.registry.register_resource("resource:HttpResourceMock", HttpResourceMock)

        resource = self.registry.get_resource(tag, {"source_language": "nl"})
        self.assertIsInstance(resource, HttpResourceMock)
        self.assertEqual(resource.config.source_language, "nl")

    def test_register_http_resource_mock_with_registered_config(self) -> None:
        tag = self.registry.register_resource("resource:HttpResourceMock", HttpResourceMock, {"source_language": "nl"})

        resource = self.registry.get_resource(tag)
        self.assertIsInstance(resource, HttpResourceMock)
        self.assertEqual(resource.config.source_language, "nl")

    def test_get_resource_overrides_registered_config(self) -> None:
        tag = self.registry.register_resource("resource:HttpResourceMock", HttpResourceMock, {"source_language": "nl"})

        resource = self.registry.get_resource(tag, {"source_language": "fr"})
        self.assertIsInstance(resource, HttpResourceMock)
        self.assertEqual(resource.config.source_language, "fr")
