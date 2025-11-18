import os
import json

from django.test import TestCase, skipUnlessDBFeature

from datagrowth.configuration import create_config
from datagrowth.resources.testing import ResourceFixturesMixin
from resources.models import HttpResourceMock


class TestResourceFixtureLoading(ResourceFixturesMixin, TestCase):

    resource_fixtures = ["http-resource-mock"]

    def test_resource_fixtures_mixin(self):
        resource = HttpResourceMock.objects.first()
        content_type, data = resource.content
        self.assertEqual(content_type, "application/json")
        self.assertNotEqual(resource.body, "en-success.json")
        resource_content_file_path = os.path.join("resources", "fixtures", "resources", "en-success.json")
        with open(resource_content_file_path, "r") as json_file:
            resource_content = json.load(json_file)
            self.assertEqual(data, resource_content)

    def test_global_cache_enabled(self):
        defaults_config = create_config("global", {})
        self.assertTrue(defaults_config.cache_only)

    @skipUnlessDBFeature("supports_sequence_reset")
    def test_resource_fixtures_sequence_reset(self):
        created = HttpResourceMock.objects.create(uri="http://localhost/sequence-check")
        self.assertGreater(created.id, 1)


class TestResourceFixtureLoadingNoCache(ResourceFixturesMixin, TestCase):

    noCache = True

    def test_global_cache_disabled(self):
        defaults_config = create_config("global", {})
        self.assertFalse(defaults_config.cache_only)
