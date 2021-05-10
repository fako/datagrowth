import json

from django.test import TestCase, Client


class TestDocumentView(TestCase):

    fixtures = ["test-data-storage"]

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.test_url = "/api/v1/datatypes/data/document/{}/"

    def test_get(self):
        response = self.client.get(self.test_url.format(1))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode("utf-8"))
        self.assertIsInstance(data, dict)
        self.assertIn("properties", data)
        response = self.client.get(self.test_url.format(666))
        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(response.status_code, 404)
        self.assertIsInstance(data, dict)
        self.assertIn("detail", data)


class TestDocumentContentView(TestCase):

    fixtures = ["test-data-storage"]

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.test_url = "/api/v1/datatypes/data/document/{}/content/"

    def test_get(self):
        response = self.client.get(self.test_url.format(1))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode("utf-8"))
        self.assertIsInstance(data, dict)
        self.assertTrue(data)
        response = self.client.get(self.test_url.format(666))
        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(response.status_code, 404)
        self.assertIsInstance(data, dict)
        self.assertIn("detail", data)
