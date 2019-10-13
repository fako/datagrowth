"""
This file tests the public interface to URLResource and how a URLResource should be used in practice.
Some core functionality shared by all derived classes of HttpResource gets tested in the core.py test module.
"""
import json

from django.test import TestCase
from django.core.exceptions import ValidationError

from datagrowth.resources import HttpResource

from resources.models import URLResourceMock
from resources.mocks.requests import MOCK_DATA


class TestURLResourceInterface(TestCase):

    def setUp(self):
        super().setUp()
        self.model = URLResourceMock
        self.content_type_header = {
            "content-type": "application/json"  # change to Accept
        }
        self.test_get_request = {
            "args": ("http://localhost:8000/new",),
            "kwargs": {},
            "method": "get",
            "url": "http://localhost:8000/new",
            "headers": {},
            "data": None,
        }
        self.test_post_request = {
            "args": ("http://localhost:8000/new",),
            "kwargs": {"query": "test"},
            "method": "post",
            "url": "http://localhost:8000/new",
            "headers": {},
            "data": {"query": "new"}
        }

    def test_http_resource_instance(self):
        # A basic check to assure that HttpResource "core" functionality gets checked for the class under test
        self.assertIsInstance(self.model(), HttpResource)

    def assert_agent_header(self, prepared_request, expected_agent):
        agent_header = prepared_request.headers.pop("User-Agent")
        datascope_agent, platform_agent = agent_header.split(";")
        self.assertEqual(datascope_agent, expected_agent)
        self.assertGreater(len(platform_agent), 0)

    def test_send_get_request(self):
        # Make a new request and store it.
        new_url = "http://localhost:8000/new"
        instance = self.model().get(new_url)
        self.assertIsNone(instance.id, "HttpResource used cache when it should have retrieved with requests")
        instance.save()
        call_args = instance.session.send.call_args
        args, kwargs = call_args
        preq = args[0]
        self.assertEqual(preq.url, new_url)
        self.assert_agent_header(preq, "DataGrowth (test)")
        self.assertEqual(preq.headers, {
            "Connection": "keep-alive",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
        })
        self.assertEqual(instance.head, self.content_type_header)
        self.assertEqual(instance.body, json.dumps(MOCK_DATA))
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.id)
        self.assertFalse(instance.data_hash)

    def test_send_post_request(self):
        # Make a new request and store it.
        new_url = "http://localhost:8000/new"
        instance = self.model().post(new_url, query="new")
        self.assertIsNone(instance.id, "HttpResource used cache when it should have retrieved with requests")
        instance.save()
        call_args = instance.session.send.call_args
        args, kwargs = call_args
        preq = args[0]
        self.assertTrue(preq.url, new_url)
        self.assert_agent_header(preq, "DataGrowth (test)")
        content_type = preq.headers.pop("Content-Type")
        self.assertEqual(content_type, "application/x-www-form-urlencoded")
        expected_body = "test=new"
        expected_length = len(expected_body)
        self.assertEqual(preq.headers, {
            "Content-Length": str(expected_length),
            "Accept": "*/*",
            "Connection": "keep-alive",
            "Accept-Encoding": "gzip, deflate",
        })
        self.assertEqual(preq.body, expected_body)
        self.assertEqual(instance.head, self.content_type_header)
        self.assertEqual(instance.body, json.dumps(MOCK_DATA))
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.id)
        self.assertTrue(instance.data_hash)

    def test_get_invalid(self):
        # Invalid invoke of get
        try:
            self.model().get()
            self.fail("Get did not raise a validation exception when invoked with invalid arguments.")
        except ValidationError:
            pass
        try:
            self.model().get("not-a-url")
            self.fail("Get did not raise a validation exception when invoked without a URL")
        except ValidationError:
            pass
        # Invalid request preset
        self.test_get_request["args"] = tuple()
        try:
            self.model(request=self.test_get_request).get()
            self.fail("Get did not raise a validation exception when confronted with an invalid preset request.")
        except ValidationError:
            pass

    def test_post_invalid(self):
        # Invalid invoke of post
        try:
            self.model().post()
            self.fail("Post did not raise a validation exception when invoked with invalid arguments.")
        except ValidationError:
            pass
        try:
            self.model().post("not-a-url")
            self.fail("Get did not raise a validation exception when invoked without a URL")
        except ValidationError:
            pass
        # Invalid request preset
        self.test_post_request["args"] = tuple()
        try:
            instance = self.model(request=self.test_post_request)
            instance.post()
            self.fail("Post did not raise a validation exception when confronted with an invalid preset request.")
        except ValidationError:
            pass
