import os
import json

from django.test import TestCase

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
