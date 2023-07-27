from types import GeneratorType
from django.test import TestCase

from datagrowth.configuration import ConfigurationType
from datagrowth.resources.http import send_iterator, send_serie_iterator
from datagrowth.processors.input import content_iterator

from resources.mocks.requests import MockRequests


class TestContentIteratorBase(TestCase):

    fixtures = ["test-http-resource-mock"]

    def setUp(self):
        super().setUp()
        self.config = ConfigurationType(
            namespace="http_resource",
            private=["_resource", "_continuation_limit"],
        )
        self.config.update({
            "resource": "resources.HttpResourceMock",
            "continuation_limit": 10
        })
        self.session = MockRequests
        self.objective = {
            "@": "$.list",
            "value": "$"
        }


class TestContentIteratorWithSendIterator(TestContentIteratorBase):

    def test_success_request(self):
        resource_iterator = send_iterator("success", method="get", config=self.config, session=self.session)
        contents = content_iterator(resource_iterator, self.objective)
        self.assertIsInstance(contents, GeneratorType)
        for ix, content in enumerate(contents):
            self.assertIsInstance(content, dict)
            self.assertEqual(len(content), 1)
            self.assertEqual(content["value"], f"value {ix}")

    def test_next_request(self):
        resource_iterator = send_iterator("next", method="get", config=self.config, session=self.session)
        contents = content_iterator(resource_iterator, self.objective)
        self.assertIsInstance(contents, GeneratorType)
        for ix, content in enumerate(contents):
            self.assertIsInstance(content, dict)
            self.assertEqual(len(content), 1)
            self.assertEqual(content["value"], f"value {ix}")

    def test_error_request(self):
        resource_iterator = send_iterator("500", method="get", config=self.config, session=self.session)
        contents = content_iterator(resource_iterator, self.objective)
        self.assertIsInstance(contents, GeneratorType)
        for _ in contents:
            self.fail("Expected error request to yield no content")


class TestContentIteratorWithSendSerieIterator(TestContentIteratorBase):

    def test_next_requests(self):
        args_list = [("success",), ("next",)]
        kwargs_list = [{}, {}]
        resource_iterator = send_serie_iterator(
            args_list, kwargs_list,
            method="get", config=self.config, session=self.session
        )
        contents = content_iterator(resource_iterator, self.objective)
        self.assertIsInstance(contents, GeneratorType)
        for ix, content in zip([0, 1, 2, 0, 1, 2, 3, 4, 5], contents):
            self.assertIsInstance(content, dict)
            self.assertEqual(len(content), 1)
            self.assertEqual(content["value"], f"value {ix}")

    def test_error_requests(self):
        args_list = [("500",), ("500",)]
        kwargs_list = [{}, {}]
        resource_iterator = send_serie_iterator(
            args_list, kwargs_list,
            method="get", config=self.config, session=self.session
        )
        contents = content_iterator(resource_iterator, self.objective)
        self.assertIsInstance(contents, GeneratorType)
        for _ in contents:
            self.fail("Expected error requests to yield no content")

    def test_mixed_success_requests(self):
        args_list = [("404",), ("success",), ("500",), ("next",)]
        kwargs_list = [{}, {}]
        resource_iterator = send_serie_iterator(
            args_list, kwargs_list,
            method="get", config=self.config, session=self.session
        )
        contents = content_iterator(resource_iterator, self.objective)
        self.assertIsInstance(contents, GeneratorType)
        for ix, content in zip([0, 1, 2, 0, 1, 2, 3, 4, 5], contents):
            self.assertIsInstance(content, dict)
            self.assertEqual(len(content), 1)
            self.assertEqual(content["value"], f"value {ix}")
