"""
This file tests the public interface to HttpResource and how a HttpResource should be used in practice.
Some core functionality shared by all derived classes of HttpResource gets tested in the core.py test module.
"""
import os
from unittest.mock import patch
from PIL.Image import Image
from datetime import datetime

from django.test import TestCase
from django.core.files import File
from django.core.files.images import ImageFile
from django.core.files.storage import default_storage
from django.core.exceptions import ValidationError

from datagrowth import settings as datagrowth_settings
from datagrowth.resources import HttpResource, HttpFileResource, file_resource_delete_handler
from datagrowth.exceptions import DGResourceDoesNotExist, DGHttpError40X

from resources.models import HttpImageResourceMock


class TestHttpImageResourceInterface(TestCase):

    fixtures = ["test-http-image-resource-mock"]

    def setUp(self):
        super().setUp()
        self.model = HttpImageResourceMock
        self.content_type_header = {
            "content-type": "image/png"  # change to Accept
        }
        self.test_get_request = {
            "args": ("test",),
            "kwargs": {},
            "method": "get",
            "url": "http://localhost:8000/test",
            "headers": {"Accept": "image/png"},
            "data": None,
        }

    def test_http_resource_instance(self):
        # A basic check to assure that HttpResource "core" functionality gets checked for the class under test
        self.assertIsInstance(self.model(), HttpResource)

    def assert_agent_header(self, prepared_request, expected_agent):
        agent_header = prepared_request.headers.pop("User-Agent")
        datascope_agent, platform_agent = agent_header.split(";")
        self.assertEqual(datascope_agent, expected_agent)
        self.assertGreater(len(platform_agent), 0)

    def assert_call_args_get(self, call_args, expected_url):
        args, kwargs = call_args
        self.assertEquals(len(args), 1)
        preq = args[0]
        self.assertEqual(preq.url, expected_url)
        self.assert_agent_header(preq, "DataGrowth (test)")
        self.assertEqual(preq.headers, {
            "Connection": "keep-alive",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
        })

    def assert_call_args_save(self, call_args, expected_file_path):
        args, kwargs = call_args
        self.assertEquals(len(args), 2)
        file_path = args[0]
        fd = args[1]
        self.assertEquals(file_path, os.path.join(datagrowth_settings.DATAGROWTH_MEDIA_ROOT, expected_file_path))
        self.assertIsInstance(fd, ImageFile)
        self.assertEquals(fd.width, 10)
        self.assertEquals(fd.height, 10)

    def test_send_get_request(self):
        default_storage_save_target = "datagrowth.resources.http.files.default_storage.save"
        # Make a few different new request and store files
        test_data = {
            "new": "resources/downloads/2/2a/new.html",
            "": "resources/downloads/6/a9/index.html",
            "new.jpg": "resources/downloads/2/2a/new.jpg",
        }
        long_test_name = "aaaaa" + 150 * "b" + ".html"
        expected_long_name = "resources/downloads/8/d7/aaaaa" + 145 * "b" + ".html"
        test_data[long_test_name] = expected_long_name
        long_test_extension = "aaaaa" + 150 * "b" + ".htmlll"
        expected_long_extension_name = "resources/downloads/8/d7/aaaaa" + 145 * "b" + ".html"
        test_data[long_test_extension] = expected_long_extension_name
        self.maxDiff = None
        for term, expected_file_path in test_data.items():
            with patch(default_storage_save_target, return_value=expected_file_path) as storage_save_mock:
                new_url = "http://localhost:8000/{}".format(term)
                instance = self.model().get(new_url)
                self.assertIsNone(instance.id, "HttpResource used cache when it should have retrieved with requests")
                self.assertEquals(storage_save_mock.call_count, 1)
                self.assert_call_args_save(storage_save_mock.call_args, expected_file_path)
                instance.save()
                self.assertEquals(instance.session.send.call_count, 1)
                self.assert_call_args_get(instance.session.send.call_args, new_url)
                self.assertEqual(instance.head, self.content_type_header)
                self.assertEqual(instance.body, expected_file_path)
                self.assertEqual(instance.status, 200)
                self.assertTrue(instance.id)
                self.assertFalse(instance.data_hash)
        # Make a new request from an existing request dictionary
        expected_file_path = "resources/downloads/8/2f/new2.html"
        with patch(default_storage_save_target, return_value=expected_file_path) as storage_save_mock:
            new_url_request = "http://localhost:8000/new2"
            request = self.model().get(new_url_request).request
            storage_save_mock.reset_mock()
            instance = self.model(request=request).get()
            self.assertIsNone(instance.id, "HttpResource used cache when it should have retrieved with requests")
            self.assertEquals(storage_save_mock.call_count, 1)
            self.assert_call_args_save(storage_save_mock.call_args, "resources/downloads/8/2f/new2.html")
            instance.save()
            self.assertEquals(instance.session.send.call_count, 1)
            self.assert_call_args_get(instance.session.send.call_args, new_url_request)
            self.assertEqual(instance.head, self.content_type_header)
            self.assertEqual(instance.body, "resources/downloads/8/2f/new2.html")
            self.assertEqual(instance.status, 200)
            self.assertTrue(instance.id)
            self.assertFalse(instance.data_hash)

    def test_get_success(self):
        # Load an existing request
        instance = self.model().get("http://localhost:8000/success")
        self.assertFalse(instance.session.send.called)
        self.assertEqual(instance.head, self.content_type_header)
        self.assertEquals(instance.body, "resources/downloads/2/60/success.html")
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.id)
        # Load an existing resource from its request
        request = instance.request
        instance = self.model(request=request).get()
        self.assertFalse(instance.session.send.called)
        self.assertEqual(instance.head, self.content_type_header)
        self.assertEquals(instance.body, "resources/downloads/2/60/success.html")
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.id)

    @patch("datagrowth.resources.http.files.default_storage.save", return_value="resources/downloads/e/11/fail.html")
    def test_get_retry(self, storage_save_mock):
        # Load and retry an existing request
        instance = self.model().get("http://localhost:8000/fail")
        self.assertEquals(instance.session.send.call_count, 1)
        self.assert_call_args_get(instance.session.send.call_args, "http://localhost:8000/fail")
        self.assertEquals(storage_save_mock.call_count, 1)
        self.assert_call_args_save(storage_save_mock.call_args, "resources/downloads/e/11/fail.html")
        self.assertEqual(instance.head, self.content_type_header)
        self.assertEqual(instance.body, "resources/downloads/e/11/fail.html")
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.id)
        # Load an existing resource from its request
        storage_save_mock.reset_mock()
        request = instance.request
        instance = self.model(request=request).get()
        self.assertEquals(instance.session.send.call_count, 1)
        self.assert_call_args_get(instance.session.send.call_args, "http://localhost:8000/fail")
        self.assertEquals(storage_save_mock.call_count, 1)
        self.assert_call_args_save(storage_save_mock.call_args, "resources/downloads/e/11/fail.html")
        self.assertEqual(instance.head, self.content_type_header)
        self.assertEqual(instance.body, "resources/downloads/e/11/fail.html")
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.id)

    def test_get_invalid(self):
        # Invalid invoke of get
        try:
            self.model().get()
            self.fail("Get did not raise a validation exception when invoked with invalid arguments.")
        except ValidationError:
            pass
        instance = self.model()
        try:
            instance.get("not-a-url")
            self.fail("Get did not raise a validation exception when invoked without a URL")
        except DGHttpError40X:
            pass
        self.assertFalse(instance.session.send.called, "Should not make request for invalid URL")
        self.assertEquals(instance.status, 404)
        self.assertEquals(instance.head, {})
        self.assertEquals(instance.body, None)
        self.assertTrue(instance.request["cancel"])
        # Invalid request preset
        self.test_get_request["args"] = tuple()
        try:
            self.model(request=self.test_get_request).get()
            self.fail("Get did not raise a validation exception when confronted with an invalid preset request.")
        except ValidationError:
            pass

    def test_get_cache_only(self):
        # Load an existing resource from cache
        instance = self.model(config={"cache_only": True}).get("http://localhost:8000/success")
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
        instance = self.model(config={"cache_only": True}).get("http://localhost:8000/fail")
        self.assertFalse(instance.session.send.called)
        self.assertEqual(instance.status, 502)
        self.assertTrue(instance.id)
        # Fail to load from cache
        try:
            self.model(config={"cache_only": True}).get("http://localhost:8000/new")
            self.fail("Missing resource in cache did not raise an exception")
        except DGResourceDoesNotExist:
            pass

    def test_post_invalid(self):
        try:
            self.model().post()
            self.fail("Post did not raise an exception, while it is not supported.")
        except NotImplementedError:
            pass

    @patch("datagrowth.resources.http.files.default_storage.open", wraps=default_storage.open)
    def test_content(self, storage_open_mock):
        # Check with successful download
        instance = HttpImageResourceMock.objects.get(id=3)  # success with actual content
        content_type, image = instance.content
        self.assertEquals(storage_open_mock.call_count, 1)
        self.assertIsInstance(image, Image)
        self.assertEquals(content_type, "image/png")
        self.assertEquals(image.width, 10)
        self.assertEquals(image.height, 10)
        # With transformation override
        storage_open_mock.reset_mock()
        transform = instance.transform
        instance.transform = lambda file: file
        content_type, image = instance.content
        self.assertEquals(storage_open_mock.call_count, 1)
        self.assertIsInstance(image, File)
        self.assertEquals(content_type, "image/png")
        instance.transform = transform
        # Check with download error
        storage_open_mock.reset_mock()
        instance = HttpImageResourceMock.objects.get(id=2)  # fail
        content_type, image = instance.content
        self.assertEquals(storage_open_mock.call_count, 0)
        self.assertIsNone(image)
        self.assertIsNone(content_type)

    def test_get_file_name(self):
        now = datetime(1970, 1, 1)
        name = HttpFileResource.get_file_name("test", now)
        self.assertEquals(name, "19700101000000000000.test")


class TestFileResourceDeleteHandler(TestCase):

    @patch("datagrowth.resources.http.files.default_storage.delete", return_value=None)
    def test_file_resource_delete_handler(self, storage_delete_mock):
        # Delete content
        instance = HttpImageResourceMock.objects.get(id=3)  # success with actual content
        file_resource_delete_handler(HttpImageResourceMock, instance, extra="ignored")
        self.assertEquals(storage_delete_mock.call_count, 1)
        # Ignore if no content at all
        storage_delete_mock.reset_mock()
        instance.body = ""
        file_resource_delete_handler(HttpImageResourceMock, instance, extra="ignored")
        self.assertEquals(storage_delete_mock.call_count, 0)
        # Ignore if file does not exist
        instance.body = "does-not-exist.png"
        file_resource_delete_handler(HttpImageResourceMock, instance, extra="ignored")
        self.assertEquals(storage_delete_mock.call_count, 0)
