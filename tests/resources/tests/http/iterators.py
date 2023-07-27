from types import GeneratorType
from unittest.mock import patch

from django.test import TestCase

from datagrowth.configuration import ConfigurationType
from datagrowth.resources.http import send_iterator, send_serie_iterator

from resources.mocks.requests import MockRequests, MockRequestsWithAgent


class TestHttpResourceIteratorBase(TestCase):

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

    def check_resources(self, resource_iterator, expected_count, expected_status):
        self.assertIsInstance(resource_iterator, GeneratorType)
        resources = []
        for resource in resource_iterator:
            self.assertIsNotNone(resource.id)
            self.assertEqual(resource.status, expected_status)
            resources.append(resource)
        self.assertEqual(len(resources), expected_count)
        return resources


class TestSendIterator(TestHttpResourceIteratorBase):

    def test_success_request(self):
        resource_iterator = send_iterator("success", method="get", config=self.config, session=self.session)
        self.check_resources(resource_iterator, 1, 200)

    def test_success_injected_session(self):
        resource_iterator = send_iterator("test", method="get", config=self.config, session=MockRequestsWithAgent)
        resources = self.check_resources(resource_iterator, 1, 200)
        self.assertIn("user-agent", resources[0].head)

    @patch("datagrowth.resources.http.iterators.get_resource_link")
    def test_success_injected_session_provider(self, get_resource_link_mock):
        _ = list(send_iterator("test", method="get", config=self.config, session="ProcessorMock"))
        args, kwargs = get_resource_link_mock.call_args
        config, session = args
        self.assertTrue(session.from_provider)

    def test_next_request(self):
        resource_iterator = send_iterator("next", method="get", config=self.config, session=self.session)
        self.check_resources(resource_iterator, 2, 200)

    def test_next_request_prohibited(self):
        self.config.continuation_limit = 1
        resource_iterator = send_iterator("next", method="get", config=self.config, session=self.session)
        self.check_resources(resource_iterator, 1, 200)

    def test_error_request(self):
        resource_iterator = send_iterator("500", method="get", config=self.config, session=self.session)
        self.check_resources(resource_iterator, 1, 500)


class TestSendSerieIterator(TestHttpResourceIteratorBase):

    def test_success_request(self):
        args_list = [("success",)]
        kwargs_list = [{}, {}]
        resource_iterator = send_serie_iterator(
            args_list, kwargs_list,
            method="get", config=self.config, session=self.session
        )
        self.check_resources(resource_iterator, 1, 200)

    def test_success_injected_session(self):
        args_list = [("test",), ("test",)]
        kwargs_list = [{}, {}]
        resource_iterator = send_serie_iterator(
            args_list, kwargs_list,
            method="get", config=self.config, session=MockRequestsWithAgent
        )
        resources = self.check_resources(resource_iterator, 2, 200)
        for resource in resources:
            self.assertIn("user-agent", resource.head)

    @patch("datagrowth.resources.http.iterators.get_resource_link")
    def test_success_injected_session_provider(self, get_resource_link_mock):
        args_list = [("test",), ("test",)]
        kwargs_list = [{}, {}]
        resource_generator = send_serie_iterator(
            args_list, kwargs_list,
            method="get", config=self.config, session="ProcessorMock"
        )
        list(resource_generator)
        for args, kwargs in get_resource_link_mock.call_args_list:
            config, session = args
            self.assertTrue(session.from_provider)

    def test_next_requests(self):
        args_list = [("success",), ("next",)]
        kwargs_list = [{}, {}]
        resource_iterator = send_serie_iterator(
            args_list, kwargs_list,
            method="get", config=self.config, session=self.session
        )
        self.check_resources(resource_iterator, 3, 200)

    def test_error_requests(self):
        args_list = [("500",), ("500",)]
        kwargs_list = [{}, {}]
        resource_iterator = send_serie_iterator(
            args_list, kwargs_list,
            method="get", config=self.config, session=self.session
        )
        self.check_resources(resource_iterator, 2, 500)
