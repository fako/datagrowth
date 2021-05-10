import json

from django.test import TestCase, Client


class TestCollectionView(TestCase):

    fixtures = ["test-data-storage"]

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.test_url = "/api/v1/datatypes/data/collection/{}/"

    def test_get(self):
        response = self.client.get(self.test_url.format(1))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode("utf-8"))
        self.assertIsInstance(data, dict)
        response = self.client.get(self.test_url.format(3))
        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(response.status_code, 404)
        self.assertIsInstance(data, dict)
        self.assertIn("detail", data)


class TestCollectionContentView(TestCase):

    fixtures = ["test-data-storage"]

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.test_url = "/api/v1/datatypes/data/collection/{}/content/"

    def test_get_success(self):
        response = self.client.get(self.test_url.format(1))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode("utf-8"))
        self.assertIsInstance(data, list)
        self.assertTrue(data)

    def test_get_not_found(self):
        response = self.client.get(self.test_url.format(3))
        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(response.status_code, 404)
        self.assertIsInstance(data, dict)
        self.assertIn("detail", data)
