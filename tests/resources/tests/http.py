from urllib.parse import urlencode
import json
from copy import deepcopy

from django.test import TestCase
from django.core.exceptions import ValidationError

from datagrowth.exceptions import DGHttpError50X, DGHttpError40X
from datagrowth.resources import HttpResource

from project.mocks.data import MOCK_DATA
from resources.models import HttpResourceMock
from resources.tests.base import ResourceTestMixin


class HttpResourceTestMixin(TestCase):

    def setUp(self):
        super(HttpResourceTestMixin, self).setUp()
        self.instance = self.get_test_instance()
        self.test_data = {"data": "test"}

    def tearDown(self):
        if "Content-Type" in self.instance.HEADERS:
            del self.instance.HEADERS["Content-Type"]

    @staticmethod
    def get_test_instance():
        raise NotImplementedError()

    def test_content(self):
        # Test access when request is missing
        content_type, data = self.instance.content
        self.assertIsNone(content_type)
        self.assertIsNone(data)
        # Test when request was made
        self.instance.head = {"content-type": "application/json; charset=utf-8"}
        self.instance.body = json.dumps(self.test_data)
        self.instance.status = 200
        content_type, data = self.instance.content
        self.assertEqual(content_type, "application/json")
        self.assertEqual(data, self.test_data)

    def test_parameters(self):
        self.assertIsInstance(self.instance.parameters(), dict)

    def test_variables(self):
        variables = self.instance.variables(["args"])
        self.assertIsInstance(variables, dict)
        self.assertIn("url", variables)
        self.assertIsInstance(variables["url"], tuple)

    def test_data(self):
        self.assertIsInstance(self.instance.data(), dict)

    def test_auth_parameters(self):
        self.assertIsInstance(self.instance.auth_parameters(), dict)

    def test_next_parameters(self):
        self.assertIsInstance(self.instance.next_parameters(), dict)

    def test_send_request_get(self):
        test_url = "http://localhost:8000/test/"
        content_header = {
            "Accept": "application/json",
            "Connection": "keep-alive",
            "Accept-Encoding": "gzip, deflate"
        }
        self.instance.request = {
            "args": tuple(),
            "kwargs": {},
            "method": "get",
            "url": test_url,
            "headers": content_header,
            "data": {},
        }
        self.instance._send()
        # See if request was made properly
        args, kwargs = self.instance.session.send.call_args
        preq = args[0]
        user_agent_header = preq.headers.pop("User-Agent", None)
        if user_agent_header is None:
            self.fail("No default User-Agent present on the request")
        self.assertEqual(preq.url, test_url)
        self.assertEqual(preq.headers, content_header)
        # Make sure that response fields are set to something and do not remain None
        self.assertIsNotNone(self.instance.head)
        self.assertIsNotNone(self.instance.body)
        self.assertIsNotNone(self.instance.status)

    def test_send_request_post(self):
        test_url = "http://localhost:8000/test/"
        test_data = {"test": "test"}
        content_header = {
            "Accept": "application/json",
            "Content-Length": "9",
            "Content-Type": "application/x-www-form-urlencoded",
            "Connection": "keep-alive",
            "Accept-Encoding": "gzip, deflate"
        }
        self.instance.request = {
            "args": tuple(),
            "kwargs": {},
            "method": "post",
            "url": test_url,
            "headers": content_header,
            "data": test_data,
        }
        self.instance._send()
        # See if request was made properly
        args, kwargs = self.instance.session.send.call_args
        preq = args[0]
        user_agent_header = preq.headers.pop("User-Agent", None)
        if user_agent_header is None:
            self.fail("No default User-Agent present on the request")
        self.assertEqual(preq.url, test_url)
        self.assertEqual(preq.headers, content_header)
        self.assertEqual(preq.body, urlencode(test_data))
        # Make sure that response fields are set to something and do not remain None
        self.assertIsNotNone(self.instance.head)
        self.assertIsNotNone(self.instance.body)
        self.assertIsNotNone(self.instance.status)

    def test_send_request_post_json(self):
        test_url = "http://localhost:8000/test/"
        test_data = {"test": "test"}
        content_header = {
            "Accept": "application/json",
            "Content-Length": "16",
            "Content-Type": "application/json",
            "Connection": "keep-alive",
            "Accept-Encoding": "gzip, deflate"
        }
        self.instance.request = {
            "args": tuple(),
            "kwargs": {},
            "method": "post",
            "url": test_url,
            "headers": content_header,
            "json": test_data,
        }
        self.instance._send()
        # See if request was made properly
        args, kwargs = self.instance.session.send.call_args
        preq = args[0]
        user_agent_header = preq.headers.pop("User-Agent", None)
        if user_agent_header is None:
            self.fail("No default User-Agent present on the request")
        self.assertEqual(preq.url, test_url)
        self.assertEqual(preq.headers, content_header)
        self.assertEqual(preq.body, json.dumps(test_data).encode("utf-8"))
        # Make sure that response fields are set to something and do not remain None
        self.assertIsNotNone(self.instance.head)
        self.assertIsNotNone(self.instance.body)
        self.assertIsNotNone(self.instance.status)

    def test_send_request_wrong(self):
        self.instance.request = None
        try:
            self.instance._send()
            self.fail("_send should fail when self.request is not set.")
        except AssertionError:
            pass

    def test_send_request_connection_error(self):
        self.skipTest("not tested")

    def test_create_request_post(self):
        request = self.instance._create_request("post", "en", "test", query="test")
        self.assertEqual(request["data"], {"test": "test"})
        self.instance.HEADERS["Content-Type"] = "application/json"
        request = self.instance._create_request("post", "en", "test", query="test")
        self.assertEqual(request["json"], {"test": "test"})

    def test_success(self):
        success_range = range(200, 209)
        for status in range(0, 999):
            self.instance.status = status
            if status in success_range:
                self.assertTrue(self.instance.success, "Success property is not True with status={}".format(status))
            else:
                self.assertFalse(self.instance.success, "Success property is not False with status={}".format(status))

    def test_handle_error(self):
        statuses_50x = range(500, 505)
        statuses_40x = range(400, 410)
        for status in statuses_50x:
            self.instance.status = status
            try:
                self.instance._handle_errors()
                self.fail("Handle error doesn't handle status {}".format(status))
            except DGHttpError50X as exc:
                self.assertIsInstance(exc.resource, HttpResource)
                self.assertEqual(exc.resource.status, status)
            except Exception as exception:
                self.fail("Handle error throws wrong exception '{}' expecting 50X".format(exception))
        for status in statuses_40x:
            self.instance.status = status
            try:
                self.instance._handle_errors()
                self.fail("Handle error doesn't handle status {}".format(status))
            except DGHttpError40X as exc:
                self.assertIsInstance(exc.resource, HttpResource)
                self.assertEqual(exc.resource.status, status)
            except Exception as exception:
                self.fail("Handle error throws wrong exception '{}' expecting 40X".format(exception))

    def test_uri_from_url(self):
        uri = HttpResource.uri_from_url("http://localhost:8000/?z=z&a=a")
        self.assertEqual(uri, "localhost:8000/?a=a&z=z")
        uri = HttpResource.uri_from_url("https://localhost:8000/?a=a&z=z")
        self.assertEqual(uri, "localhost:8000/?a=a&z=z")

    def test_hash_from_data(self):
        # Give no data
        data_hash = HttpResource.hash_from_data({})
        self.assertEqual(data_hash, "")
        # Give data
        data_hash = HttpResource.hash_from_data(self.test_data)
        self.assertIsInstance(data_hash, str)
        # Compare with slightly altered data
        self.test_data["data"] = "tezt"
        data_hash2 = HttpResource.hash_from_data(self.test_data)
        self.assertNotEqual(data_hash, data_hash2)

    def test_set_error(self):
        self.instance.set_error(404)
        self.assertEqual(self.instance.head, {})
        self.assertIsNone(self.instance.body)
        self.assertEqual(self.instance.status, 404)
        self.instance.set_error(0, True)
        self.assertEqual(self.instance.head, {})
        self.assertEqual(self.instance.body, "")
        self.assertEqual(self.instance.status, 0)


class ConfigurationFieldTestMixin(TestCase):

    def setUp(self):
        super(ConfigurationFieldTestMixin, self).setUp()
        self.instance = self.get_test_instance()
        self.model = self.instance.__class__

    @staticmethod
    def get_test_instance():
        raise NotImplementedError("Should return the model that holds the configuration field.")

    def fill_test_instance(self):
        raise NotImplementedError("Should make self.instance ready for save by filling required fields.")

    def test_set_storage_load_and_get(self):
        self.fill_test_instance()
        self.instance.config = {"test": "loaded"}
        self.assertEqual(self.instance.config.test, "loaded")
        self.instance.save()
        new = self.model.objects.get(id=self.instance.id)
        self.assertEqual(new.config.test, "loaded")


class TestHttpResourceMock(ResourceTestMixin, HttpResourceTestMixin, ConfigurationFieldTestMixin):

    fixtures = ["test-http-resource-mock"]

    @staticmethod
    def get_test_instance():
        return HttpResourceMock()

    def fill_test_instance(self):
        self.instance.uri = "uri"
        self.instance.data_hash = "12345"
        self.instance.head = {"json": "test"}
        self.instance.body = "response"
        self.instance.status = 200

    def setUp(self):
        super(TestHttpResourceMock, self).setUp()
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
            "Accept-Encoding": "gzip, deflate"
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
            "Accept-Encoding": "gzip, deflate"
        })
        self.assertEqual(preq.body, expected_body)

    def test_init(self):
        mock = HttpResourceMock()
        self.assertEqual(mock.timeout, 30)
        mock = HttpResourceMock(timeout=20)
        self.assertEqual(mock.timeout, 20)

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
        self.skipTest("not tested")

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
        # Invalid invoke of get
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
        self.skipTest("not tested")

    def test_request_with_auth(self):
        self.instance.request = self.test_post_request
        request = self.instance.request_with_auth()
        self.assertIn("auth=1", request["url"])
        self.assertNotIn("auth=1", self.instance.request["url"], "request_with_auth should not alter existing request")
        self.assertIn("key=oehhh", request["url"])
        self.assertNotIn("key=oehhh", self.instance.request["url"], "request_with_auth should not alter existing request")
        self.assertEqual(request["data"], self.test_post_request["data"])
        self.skipTest("test the auth with headers")

    def test_request_without_auth(self):
        self.instance.request = deepcopy(self.test_post_request)
        self.instance.request["url"] = self.test_post_request["url"] + "&auth=1&key=ahhh"
        request = self.instance.request_without_auth()
        self.assertNotIn("auth=1", request["url"])
        self.assertIn("auth=1", self.instance.request["url"], "request_without_auth should not alter existing request")
        self.assertNotIn("key=oehhh", request["url"])
        self.assertIn("key=ahhh", self.instance.request["url"], "request_without_auth should not alter existing request")
        self.assertEqual(request["data"], self.test_post_request["data"])
        self.skipTest("test the auth with headers")

    def test_create_next_request(self):
        # Test with get
        instance = self.model().get("next")
        request = instance.create_next_request()
        self.assertIsNotNone(request)
        self.assertIn("next=1", request["url"])
        self.assertNotIn("auth=1", instance.request["url"], "create_next_request should not alter existing request")
        # Test with post
        instance = self.model().post(query="next")
        request = instance.create_next_request()
        self.assertIsNotNone(request)
        self.assertIn("next=1", request["url"])
        self.assertNotIn("auth=1", instance.request["url"], "create_next_request should not alter existing request")
        instance = self.model().post(query="next", file="text-file.txt")
        request = instance.create_next_request()
        self.assertIsNotNone(request)
        self.assertIn("next=1", request["url"])
        self.assertNotIn("auth=1", instance.request["url"], "create_next_request should not alter existing request")
        # Test that None is returned when there is no continuation
        instance = self.model().get("success")
        request = instance.create_next_request()
        self.assertIsNone(request)
        instance = self.model().post(query="success")
        request = instance.create_next_request()
        self.assertIsNone(request)
        instance = self.model().post(query="success", file="text-file.txt")
        request = instance.create_next_request()
        self.assertIsNone(request)

    def test_validate_request_args(self):  # using GET
        # Valid
        try:
            self.instance.validate_request(self.test_get_request)
        except ValidationError:
            self.fail("validate_request raised for a valid request.")
        # Invalid
        invalid_request = deepcopy(self.test_get_request)
        invalid_request["args"] = ("en", "en", "test")
        try:
            self.instance.validate_request(invalid_request)
            self.fail("validate_request did not raise with invalid args for schema.")
        except ValidationError:
            pass
        invalid_request["args"] = tuple()
        try:
            self.instance.validate_request(invalid_request)
            self.fail("validate_request did not raise with invalid args for schema.")
        except ValidationError:
            pass
        # No schema
        self.instance.GET_SCHEMA["args"] = None
        try:
            self.instance.validate_request(self.test_get_request)
            self.fail("validate_request did not raise with invalid args for no schema.")
        except ValidationError:
            pass
        # Always valid schema
        self.instance.GET_SCHEMA["args"] = {}
        try:
            self.instance.validate_request(invalid_request)
        except ValidationError:
            self.fail("validate_request invalidated with a schema without restrictions.")

    def test_validate_request_kwargs(self):  # using POST
        # Valid
        try:
            self.instance.validate_request(self.test_post_request)
        except ValidationError:
            self.fail("validate_request raised for a valid request.")
        # Invalid
        invalid_request = deepcopy(self.test_post_request)
        invalid_request["kwargs"] = {"query": 1}
        try:
            self.instance.validate_request(invalid_request)
            self.fail("validate_request did not raise with invalid kwargs for schema.")
        except ValidationError:
            pass
        invalid_request["kwargs"] = {}
        try:
            self.instance.validate_request(invalid_request)
            self.fail("validate_request did not raise with invalid kwargs for schema.")
        except ValidationError:
            pass
        # No schema
        self.instance.POST_SCHEMA["kwargs"] = None
        try:
            self.instance.validate_request(self.test_post_request)
            self.fail("validate_request did not raise with invalid kwargs for no schema.")
        except ValidationError:
            pass
        # Always valid schema
        self.instance.POST_SCHEMA["kwargs"] = {}
        try:
            self.instance.validate_request(invalid_request)
        except ValidationError:
            self.fail("validate_request invalidated with a schema without restrictions.")

    def test_clean_get(self):
        self.instance.request = self.test_get_request
        self.instance.clean()
        self.assertEqual(self.instance.uri, "localhost:8000/en/?q=test")
        self.assertEqual(self.instance.data_hash, "")
        self.assertIsNone(self.instance.purge_at)

    def test_clean_post(self):
        self.instance.request = self.test_post_request
        self.instance.clean()
        self.assertEqual(self.instance.uri, "localhost:8000/en/?q=test")
        self.assertEqual(self.instance.data_hash, "c6ce96ff340b2fa4ead97ae01efa7fe20ca727bb")
        self.assertIsNone(self.instance.purge_at)

    def test_user_agent(self):
        instance = self.model(config={"user_agent": "DataScope (custom)"}).get("agent")
        self.assertTrue(instance.session.send.called)
        self.assertEqual(instance.head, self.content_type_header)
        self.assertEqual(instance.body, json.dumps(MOCK_DATA))
        self.assertEqual(instance.status, 200)
        self.assertFalse(instance.data_hash)
        args, kwargs = instance.session.send.call_args
        preq = args[0]
        self.assert_agent_header(preq, "DataScope (custom)")

    def test_get_data_key(self):
        # Post request
        post_request = self.test_post_request
        data_key = self.instance._get_data_key(post_request)
        self.assertEqual(data_key, "data")
        data = post_request.pop("data")
        post_request["json"] = data
        data_key = self.instance._get_data_key(post_request)
        self.assertEqual(data_key, "json")
        # Get request
        get_request = self.test_get_request
        data_key = self.instance._get_data_key(get_request)
        self.assertEqual(data_key, "data")
        data = get_request.pop("data")
        get_request["json"] = data
        data_key = self.instance._get_data_key(get_request)
        self.assertEqual(data_key, "json")
        # Through headers
        content_header = {
            "Accept": "application/json",
            "Content-Length": "9",
            "Content-Type": "application/x-www-form-urlencoded",
            "Connection": "keep-alive",
            "Accept-Encoding": "gzip, deflate"
        }
        data_key = self.instance._get_data_key({}, content_header)
        self.assertEqual(data_key, "data")
        content_header["Content-Type"] = "application/json"
        data_key = self.instance._get_data_key({}, content_header)
        self.assertEqual(data_key, "json")

    def test_parse_content_type(self):
        self.skipTest("not tested")
