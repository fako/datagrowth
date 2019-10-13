"""
This file tests the public interface to HttpResource and how a HttpResource should be used in practice.
Some core functionality shared by all derived classes of HttpResource gets tested in the core.py test module.
"""

import json

from django.test import TestCase
from django.core.exceptions import ValidationError

from datagrowth.resources import HttpResource
from datagrowth.exceptions import DGResourceDoesNotExist

from resources.models import HttpResourceMock
from resources.mocks.requests import MOCK_DATA


class TestHttpResourceInterface(TestCase):

    fixtures = ["test-http-resource-mock"]

    def setUp(self):
        super().setUp()
        self.model = HttpResourceMock
        self.content_type_header = {
            "content-type": "application/json"  # change to Accept
        }
        self.test_get_request = {
            "args": ("en", "test",),
            "kwargs": {},
            "method": "get",
            "url": "http://localhost:8000/en/?q=test",
            "headers": {"Accept": "application/json"},
            "data": None,
        }
        self.test_post_request = {
            "args": ("en", "test",),
            "kwargs": {"query": "test"},
            "method": "post",
            "url": "http://localhost:8000/en/?q=test",
            "headers": {"Accept": "application/json"},
            "data": {"test": "test"}
        }

    def test_http_resource_instance(self):
        # A basic check to assure that HttpResource "core" functionality gets checked for the class under test
        self.assertIsInstance(self.model(), HttpResource)

    def assert_agent_header(self, prepared_request, expected_agent):
        agent_header = prepared_request.headers.pop("User-Agent")
        datascope_agent, platform_agent = agent_header.split(";")
        self.assertEqual(datascope_agent, expected_agent)
        self.assertGreater(len(platform_agent), 0)

    def assert_form_content_type(self, prepared_request):
        content_type = prepared_request.headers.pop("Content-Type")
        content_type_partial, boundary = content_type.split("=")
        self.assertEqual(content_type_partial, "multipart/form-data; boundary")
        return boundary

    def assert_content_type(self, prepared_request):
        content_type = prepared_request.headers.pop("Content-Type")
        self.assertEqual(content_type, "application/x-www-form-urlencoded")

    def assert_call_args_get(self, call_args, term):
        expected_url = "http://localhost:8000/en/?q={}&key=oehhh&auth=1&param=1&meta={}".format(term, term)
        args, kwargs = call_args
        preq = args[0]
        self.assertTrue(preq.url.startswith("http://localhost:8000/en/?"))
        self.assertIn("q={}".format(term), preq.url)
        self.assertIn("key=oehhh", preq.url)
        self.assertIn("auth=1", preq.url)
        self.assertIn("param=1", preq.url)
        self.assertIn("meta={}".format(term), preq.url)
        self.assertEqual(len(expected_url), len(preq.url))
        self.assert_agent_header(preq, "DataGrowth (test)")
        self.assertEqual(preq.headers, {
            "Connection": "keep-alive",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
            "Authorization": "Bearer oehhh"
        })

    def assert_call_args_post(self, call_args, term, is_form=False):
        expected_url = "http://localhost:8000/en/?q={}&key=oehhh&auth=1&param=1&meta={}".format(term, term)
        args, kwargs = call_args
        preq = args[0]
        self.assertTrue(preq.url.startswith("http://localhost:8000/en/?"))
        self.assertIn("q={}".format(term), preq.url)
        self.assertIn("key=oehhh", preq.url)
        self.assertIn("auth=1", preq.url)
        self.assertIn("param=1", preq.url)
        self.assertIn("meta={}".format(term), preq.url)
        self.assertEqual(len(expected_url), len(preq.url))
        self.assert_agent_header(preq, "DataGrowth (test)")
        if is_form:
            boundary = self.assert_form_content_type(preq)
            expected_body = bytes(
                '--{boundary}\r\nContent-Disposition: form-data; name="test"\r\n\r\n{term}\r\n'
                '--{boundary}\r\nContent-Disposition: form-data; name="file"; '
                'filename="text-file.txt"\r\n\r\na test text file\n\r\n'
                '--{boundary}--\r\n'.format(term=term, boundary=boundary),
                encoding="utf-8"
            )
            expected_length = len(expected_body)
        else:
            self.assert_content_type(preq)
            expected_body = "test={}".format(term)
            expected_length = len(expected_body)
        self.assertEqual(preq.headers, {
            "Content-Length": str(expected_length),
            "Accept": "application/json",
            "Connection": "keep-alive",
            "Accept-Encoding": "gzip, deflate",
            "Authorization": "Bearer oehhh"
        })
        self.assertEqual(preq.body, expected_body)

    def test_send_get_request(self):
        # Make a new request and store it.
        instance = self.model().get("new")
        self.assertIsNone(instance.id, "HttpResource used cache when it should have retrieved with requests")
        instance.save()
        self.assert_call_args_get(instance.session.send.call_args, "new")
        self.assertEqual(instance.head, self.content_type_header)
        self.assertEqual(instance.body, json.dumps(MOCK_DATA))
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.id)
        self.assertFalse(instance.data_hash)
        # Make a new request from an existing request dictionary
        request = self.model().get("new2").request
        instance = self.model(request=request).get()
        self.assertIsNone(instance.id, "HttpResource used cache when it should have retrieved with requests")
        instance.save()
        self.assert_call_args_get(instance.session.send.call_args, "new2")
        self.assertEqual(instance.head, self.content_type_header)
        self.assertEqual(instance.body, json.dumps(MOCK_DATA))
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.id)
        self.assertFalse(instance.data_hash)

    def test_get_success(self):
        # Load an existing request
        instance = self.model().get("success")
        self.assertFalse(instance.session.send.called)
        self.assertEqual(instance.head, self.content_type_header)
        self.assertJSONEqual(instance.body, json.dumps(MOCK_DATA))
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.id)
        # Load an existing resource from its request
        request = instance.request
        instance = self.model(request=request).get()
        self.assertFalse(instance.session.send.called)
        self.assertEqual(instance.head, self.content_type_header)
        self.assertJSONEqual(instance.body, json.dumps(MOCK_DATA))
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.id)

    def test_get_retry(self):
        # Load and retry an existing request
        instance = self.model().get("fail")
        self.assert_call_args_get(instance.session.send.call_args, "fail")
        self.assertEqual(instance.head, self.content_type_header)
        self.assertEqual(instance.body, json.dumps(MOCK_DATA))
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.id)
        # Load an existing resource from its request
        request = instance.request
        instance = self.model(request=request).get()
        self.assert_call_args_get(instance.session.send.call_args, "fail")
        self.assertEqual(instance.head, self.content_type_header)
        self.assertEqual(instance.body, json.dumps(MOCK_DATA))
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.id)

    def test_get_invalid(self):
        # Invalid invoke of get
        try:
            self.model().get()
            self.fail("Get did not raise a validation exception when invoked with invalid arguments.")
        except ValidationError:
            pass
        # Invalid request preset
        self.test_get_request["args"] = tuple()
        try:
            self.model(request=self.test_get_request).get()
            self.fail("Get did not raise a validation exception when confronted with an invalid preset request.")
        except ValidationError:
            pass

    def test_get_cache_only(self):
        # Load an existing resource from cache
        instance = self.model(config={"cache_only": True}).get("success")
        self.assertFalse(instance.session.send.called)
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.id)
        # Load an existing resource from cache by its request
        request = instance.request
        instance = self.model(request=request, config={"cache_only": True}).get()
        self.assertFalse(instance.session.send.called)
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.id)
        # Load a failed resource from cache
        instance = self.model(config={"cache_only": True}).get("fail")
        self.assertFalse(instance.session.send.called)
        self.assertEqual(instance.status, 502)
        self.assertTrue(instance.id)
        # Fail to load from cache
        try:
            self.model(config={"cache_only": True}).get("new")
            self.fail("Missing resource in cache did not raise an exception")
        except DGResourceDoesNotExist:
            pass

    def test_send_post_request(self):
        # Make a new request and store it.
        instance = self.model().post(query="new")
        self.assertIsNone(instance.id, "HttpResource used cache when it should have retrieved with requests")
        instance.save()
        self.assert_call_args_post(instance.session.send.call_args, "new")
        self.assertEqual(instance.head, self.content_type_header)
        self.assertEqual(instance.body, json.dumps(MOCK_DATA))
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.id)
        self.assertTrue(instance.data_hash)
        # Make a new request from an existing request dictionary
        request = self.model().post(query="new2").request
        instance = self.model(request=request).post()
        self.assertIsNone(instance.id, "HttpResource used cache when it should have retrieved with requests")
        instance.save()
        self.assert_call_args_post(instance.session.send.call_args, "new2")
        self.assertEqual(instance.head, self.content_type_header)
        self.assertEqual(instance.body, json.dumps(MOCK_DATA))
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.id)
        self.assertTrue(instance.data_hash)
        # Make a new request containing a file and store it.
        instance = self.model().post(query="new3", file="text-file.txt")
        self.assertIsNone(instance.id, "HttpResource used cache when it should have retrieved with requests")
        instance.save()
        self.assert_call_args_post(instance.session.send.call_args, "new3", is_form=True)
        self.assertEqual(instance.head, self.content_type_header)
        self.assertEqual(instance.body, json.dumps(MOCK_DATA))
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.id)
        self.assertTrue(instance.data_hash)
        # Make a new request from an existing request dictionary and a file
        request = self.model().post(query="new4", file="text-file.txt").request
        instance = self.model(request=request).post()
        self.assertIsNone(instance.id, "HttpResource used cache when it should have retrieved with requests")
        instance.save()
        self.assert_call_args_post(instance.session.send.call_args, "new4", is_form=True)
        self.assertEqual(instance.head, self.content_type_header)
        self.assertEqual(instance.body, json.dumps(MOCK_DATA))
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.id)
        self.assertTrue(instance.data_hash)

    def test_post_success(self):
        # Load an existing request
        instance = self.model().post(query="success")
        self.assertFalse(instance.session.send.called, "HttpResource called requests.send when expected to use cache")
        self.assertIsNotNone(instance.id, "HttpResource without id when expected to use cache")
        self.assertEqual(instance.head, self.content_type_header)
        self.assertJSONEqual(instance.body, json.dumps(MOCK_DATA))
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.id)
        self.assertTrue(instance.data_hash)
        # Load an existing resource from its request
        request = instance.request
        instance = self.model(request=request).post()
        self.assertFalse(instance.session.send.called, "HttpResource called requests.send when expected to use cache")
        self.assertIsNotNone(instance.id, "HttpResource without id when expected to use cache")
        self.assertEqual(instance.head, self.content_type_header)
        self.assertJSONEqual(instance.body, json.dumps(MOCK_DATA))
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.id)
        self.assertTrue(instance.data_hash)
        # Load an existing request with a file attachment
        instance = self.model().post(query="success", file="text-file.txt")
        self.assertFalse(instance.session.send.called, "HttpResource called requests.send when expected to use cache")
        self.assertIsNotNone(instance.id, "HttpResource without id when expected to use cache")
        self.assertEqual(instance.head, self.content_type_header)
        self.assertJSONEqual(instance.body, json.dumps(MOCK_DATA))
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.id)
        self.assertTrue(instance.data_hash)
        # Load an existing resource from its request with a file attachment
        request = instance.request
        instance = self.model(request=request).post()
        self.assertFalse(instance.session.send.called, "HttpResource called requests.send when expected to use cache")
        self.assertIsNotNone(instance.id, "HttpResource without id when expected to use cache")
        self.assertEqual(instance.head, self.content_type_header)
        self.assertJSONEqual(instance.body, json.dumps(MOCK_DATA))
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.id)
        self.assertTrue(instance.data_hash)

    def test_post_retry(self):
        # Load and retry an existing request
        instance = self.model().post(query="fail")
        self.assertIsNotNone(instance.id, "HttpResource without id when expected to use cache")
        self.assert_call_args_post(instance.session.send.call_args, "fail")
        self.assertEqual(instance.head, self.content_type_header)
        self.assertEqual(instance.body, json.dumps(MOCK_DATA))
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.id)
        self.assertTrue(instance.data_hash)
        # Load an existing resource from its request
        request = instance.request
        instance = self.model(request=request).post()
        self.assertIsNotNone(instance.id, "HttpResource without id when expected to use cache")
        self.assert_call_args_post(instance.session.send.call_args, "fail")
        self.assertEqual(instance.head, self.content_type_header)
        self.assertEqual(instance.body, json.dumps(MOCK_DATA))
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.id)
        self.assertTrue(instance.data_hash)
        # Load and retry an existing request with a file
        instance = self.model().post(query="fail", file="text-file.txt")
        self.assertIsNotNone(instance.id, "HttpResource without id when expected to use cache")
        self.assert_call_args_post(instance.session.send.call_args, "fail", is_form=True)
        self.assertEqual(instance.head, self.content_type_header)
        self.assertEqual(instance.body, json.dumps(MOCK_DATA))
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.id)
        self.assertTrue(instance.data_hash)
        # Load an existing resource from its request with a file
        request = instance.request
        instance = self.model(request=request).post()
        self.assertIsNotNone(instance.id, "HttpResource without id when expected to use cache")
        self.assert_call_args_post(instance.session.send.call_args, "fail", is_form=True)
        self.assertEqual(instance.head, self.content_type_header)
        self.assertEqual(instance.body, json.dumps(MOCK_DATA))
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.id)
        self.assertTrue(instance.data_hash)

    def test_post_invalid(self):
        # Invalid invoke of post
        try:
            self.model().post()
            self.fail("Post did not raise a validation exception when invoked with invalid arguments.")
        except ValidationError:
            pass
        # Invalid request preset
        self.test_post_request["kwargs"] = {}
        try:
            self.model(request=self.test_post_request).post()
            self.fail("Post did not raise a validation exception when confronted with an invalid preset request.")
        except ValidationError:
            pass

    def test_post_cache_only(self):
        # Load an existing resource from cache
        instance = self.model(config={"cache_only": True}).post(query="success")
        self.assertFalse(instance.session.send.called)
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.id)
        file_instance = self.model(config={"cache_only": True}).post(query="success", file="text-file.txt")
        self.assertFalse(file_instance.session.send.called)
        self.assertEqual(file_instance.status, 200)
        self.assertTrue(file_instance.id)
        # Load an existing resource from cache by its request
        request = instance.request
        instance = self.model(request=request, config={"cache_only": True}).post()
        self.assertFalse(instance.session.send.called)
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.id)
        request = file_instance.request
        instance = self.model(request=request, config={"cache_only": True}).post()
        self.assertFalse(instance.session.send.called)
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.id)
        # Load a failed resource from cache
        instance = self.model(config={"cache_only": True}).post(query="fail", file="text-file.txt")
        self.assertFalse(instance.session.send.called)
        self.assertEqual(instance.status, 502)
        self.assertTrue(instance.id)
        instance = self.model(config={"cache_only": True}).post(query="fail", file="text-file.txt")
        self.assertFalse(instance.session.send.called)
        self.assertEqual(instance.status, 502)
        self.assertTrue(instance.id)
        # Fail to load from cache
        try:
            self.model(config={"cache_only": True}).post(query="new")
            self.fail("Missing resource in cache did not raise an exception")
        except DGResourceDoesNotExist:
            pass
        try:
            self.model(config={"cache_only": True}).post(query="new", file="text-file.txt")
            self.fail("Missing resource (with file) in cache did not raise an exception")
        except DGResourceDoesNotExist:
            pass
