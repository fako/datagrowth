from django.test import TestCase

from datagrowth.registry import Registry
from resources.models import HttpResourceMock


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
