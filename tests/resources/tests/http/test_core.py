"""
This file tests some core functionality by testing with HttpResourceMock instances.
However these tests are assumed to be important for all derived classes of HttpResource.
In that sense it is testing the "core" of HttpResource through HttpResourceMock.

The tests of the actual interface to HttpResource and how a HttpResource should be used in practice
is present in the generic.py test module.
"""

from unittest.mock import patch, call
from urllib.parse import urlencode
import json
from copy import deepcopy
from requests.exceptions import SSLError, ConnectionError, Timeout

from django.core.exceptions import ValidationError

from datagrowth.exceptions import DGHttpError50X, DGHttpError40X
from datagrowth.resources import HttpResource
from datagrowth.configuration.types import ConfigurationType

from project.mocks.data import MOCK_DATA
from resources.models import HttpResourceMock
from resources.tests import base as resources_test_base
from resources.mocks.requests import get_erroneous_requests_mock, MockRequests


class TestHttpResource(resources_test_base.ResourceTestMixin):

    fixtures = ["test-http-resource-mock"]

    @staticmethod
    def get_test_instance(session=None, config=None):
        config = config or {}
        return HttpResourceMock(session=session, config=config)

    @staticmethod
    def get_test_class():
        return HttpResourceMock

    def setUp(self):
        self.instance = self.get_test_instance()
        self.test_data = {"data": "test", "atad": {"test": "test", "tset": "test"}}
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

    def tearDown(self):
        if "Content-Type" in self.instance.HEADERS:
            del self.instance.HEADERS["Content-Type"]

    @patch("datagrowth.resources.http.generic.HttpResource.send")
    def test_extract(self, send_mock):
        resource = self.instance.extract("get", "test", test="test")
        self.assertIsNotNone(resource)
        send_mock.assert_called_with("get", "en", "test", test="test")
        send_mock.reset()
        resource = self.instance.extract("get", test="test")
        self.assertIsNotNone(resource)

    def test_configuration(self):
        self.assertIsInstance(self.instance.config, ConfigurationType)

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
        # Variables with explicit input
        variables = self.instance.variables("arg1", "arg2")
        self.assertIsInstance(variables, dict)
        self.assertIn("url", variables)
        self.assertIn("meta", variables)
        self.assertEqual(variables["url"], ("arg1", "arg2"))
        self.assertEqual(variables["meta"], "arg2")
        # Variables without input
        variables = self.instance.variables()
        self.assertIsInstance(variables, dict)
        self.assertIn("url", variables)
        self.assertIn("meta", variables)
        self.assertEqual(variables["url"], tuple())
        self.assertIsNone(variables["meta"])
        # Variables with input through get
        self.instance.get("success")
        variables = self.instance.variables()
        self.assertIn("url", variables)
        self.assertIn("meta", variables)
        self.assertEqual(variables["url"], ("en", "success"))
        self.assertEqual(variables["meta"], "success")

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
        self.assertEqual(self.instance.session.send.call_count, 1)
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
        self.assertEqual(self.instance.session.send.call_count, 1)
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
        self.assertEqual(self.instance.session.send.call_count, 1)
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
        self.instance.request = "http://localhost:8000/success"
        try:
            self.instance._send()
            self.fail("_send should fail when self.request is not a dictionary.")
        except AssertionError:
            pass

    @patch("datagrowth.resources.http.generic.sleep")
    def test_get_request_connection_error(self, sleep_mock):
        exceptions_with_status = {
            SSLError: 496,
            ConnectionError: 502,
            IOError: 502,
            Timeout: 504,
            UnicodeDecodeError("utf-8", b"abc", 0, 1, "message"): 600
        }
        for exception, exception_status in exceptions_with_status.items():
            error_session = get_erroneous_requests_mock(exception)
            instance = self.get_test_instance(session=error_session)
            try:
                instance.get("error-get")
                self.fail("Connection error did not raise for GET exception: {}".format(exception))
            except (DGHttpError40X, DGHttpError50X):
                pass
            self.assertEqual(instance.status, exception_status)
            self.assertEqual(instance.head, {})
            self.assertEqual(instance.body, "")
            if exception_status in [502, 504]:
                self.assertEqual(instance.request["backoff_delay"], 16)
            else:
                self.assertEqual(instance.request["backoff_delay"], False)
        self.assertEqual(
            sleep_mock.call_count, 17,
            "Expected three errors to call sleep five times during backoff procedure"
        )
        self.assertEqual(sleep_mock.call_args_list[0], call(0))

    @patch("datagrowth.resources.http.generic.sleep")
    def test_post_request_connection_error(self, sleep_mock):
        exceptions_with_status = {
            SSLError: 496,
            ConnectionError: 502,
            IOError: 502,
            Timeout: 504,
            UnicodeDecodeError("utf-8", b"abc", 0, 1, "message"): 600
        }
        for exception, exception_status in exceptions_with_status.items():
            error_session = get_erroneous_requests_mock(exception)
            instance = self.get_test_instance(session=error_session)
            try:
                instance.post(query="error-post")
                self.fail("Connection error did not raise for POST exception: {}".format(exception))
            except (DGHttpError40X, DGHttpError50X):
                pass
            self.assertEqual(instance.status, exception_status)
            self.assertEqual(instance.head, {})
            self.assertEqual(instance.body, "")
            if exception_status in [502, 504]:
                self.assertEqual(instance.request["backoff_delay"], 16)
            else:
                self.assertEqual(instance.request["backoff_delay"], False)
        self.assertEqual(
            sleep_mock.call_count, 17,
            "Expected three errors to call sleep five times during backoff procedure"
        )
        self.assertEqual(sleep_mock.call_args_list[0], call(0))

    def test_request_cancel(self):
        MockRequests.send.reset()
        request = {"cancel": True}
        # Testing with default status code
        instance = self.get_test_instance(MockRequests)
        instance.request = request
        instance._send()
        self.assertEqual(instance.status, 113)
        self.assertEqual(instance.head, {})
        self.assertEqual(instance.body, "")
        self.assertFalse(MockRequests.send.called)
        # Testing with custom status code
        instance = self.get_test_instance(MockRequests)
        instance.status = 1
        instance.request = request
        instance._send()
        self.assertEqual(instance.status, 1, "Expected Resource to take on non-default status when it's supplied")
        self.assertEqual(instance.head, {})
        self.assertEqual(instance.body, "")
        self.assertFalse(MockRequests.send.called)

    def test_request_no_cancel(self):
        test_url = "http://localhost:8000/test/"
        content_header = {
            "Accept": "application/json",
            "Connection": "keep-alive",
            "Accept-Encoding": "gzip, deflate"
        }
        request = {
            "args": tuple(),
            "kwargs": {},
            "method": "get",
            "url": test_url,
            "headers": content_header,
            "data": {},
            "cancel": False  # testing no cancellation
        }
        instance = self.get_test_instance(MockRequests)
        instance.request = request
        instance._send()
        self.assertEqual(instance.status, 200)
        self.assertTrue(instance.body)
        self.assertTrue(instance.head)
        self.assertTrue(MockRequests.send.called)

    @patch("datagrowth.resources.http.generic.sleep")
    def test_get_request_connection_error_no_backoff_delay(self, sleep_mock):
        exceptions_with_status = {
            SSLError: 496,
            ConnectionError: 502
        }
        for exception, exception_status in exceptions_with_status.items():
            error_session = get_erroneous_requests_mock(exception)
            instance = self.get_test_instance(session=error_session, config={"backoff_delays": []})
            try:
                instance.get("error-get")
                self.fail("Connection error did not raise for GET exception: {}".format(exception))
            except (DGHttpError40X, DGHttpError50X):
                pass
            self.assertEqual(instance.request["backoff_delay"], False)
        self.assertEqual(sleep_mock.call_args_list, [call(0), call(0)])

    @patch("datagrowth.resources.http.generic.sleep")
    def test_post_request_connection_error_no_backoff_delay(self, sleep_mock):
        exceptions_with_status = {
            SSLError: 496,
            ConnectionError: 502
        }
        for exception, exception_status in exceptions_with_status.items():
            error_session = get_erroneous_requests_mock(exception)
            instance = self.get_test_instance(session=error_session, config={"backoff_delays": []})
            try:
                instance.get("error-get")
                self.fail("Connection error did not raise for POST exception: {}".format(exception))
            except (DGHttpError40X, DGHttpError50X):
                pass
            self.assertEqual(instance.request["backoff_delay"], False)
        self.assertEqual(sleep_mock.call_args_list, [call(0), call(0)])

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

    def test_handle_errors(self):
        statuses_50x = range(500, 505)
        statuses_40x = range(400, 410)
        for status in statuses_50x:
            self.instance.status = status
            try:
                self.instance.handle_errors()
                self.fail("Handle error doesn't handle status {}".format(status))
            except DGHttpError50X as exc:
                self.assertIsInstance(exc.resource, HttpResource)
                self.assertEqual(exc.resource.status, status)
            except Exception as exception:
                self.fail("Handle error throws wrong exception '{}' expecting 50X".format(exception))
        for status in statuses_40x:
            self.instance.status = status
            try:
                self.instance.handle_errors()
                self.fail("Handle error doesn't handle status {}".format(status))
            except DGHttpError40X as exc:
                self.assertIsInstance(exc.resource, HttpResource)
                self.assertEqual(exc.resource.status, status)
            except Exception as exception:
                self.fail("Handle error throws wrong exception '{}' expecting 40X".format(exception))

    def test_uri_from_url(self):
        uri = HttpResource.uri_from_url("http://localhost:8000/?z=z&a=a")
        self.assertEqual(uri, "localhost:8000/?a=a&z=z")
        uri = HttpResource.uri_from_url("https://localhost:8000/?a=z&z=a")
        self.assertEqual(uri, "localhost:8000/?a=z&z=a")

    def test_hash_from_data(self):
        # Give no data
        data_hash = HttpResource.hash_from_data({})
        self.assertEqual(data_hash, "")
        # Give data
        data_hash = HttpResource.hash_from_data(self.test_data)
        self.assertEqual(
            data_hash, "22678875db79b37d27f3a7ae598e65c72eb55c36",
            "Data hashes do not match, perhaps keys were not sorted before JSON dump?"
        )
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

    def assert_agent_header(self, prepared_request, expected_agent):
        agent_header = prepared_request.headers.pop("User-Agent")
        datascope_agent, platform_agent = agent_header.split(";")
        self.assertEqual(datascope_agent, expected_agent)
        self.assertGreater(len(platform_agent), 0)

    def test_init(self):
        mock = HttpResourceMock()
        self.assertEqual(mock.timeout, 30)
        mock = HttpResourceMock(timeout=20)
        self.assertEqual(mock.timeout, 20)

    def test_request_with_auth(self):
        self.instance.request = self.test_post_request
        request = self.instance.request_with_auth()
        self.assertIn("auth=1", request["url"])
        self.assertNotIn("auth=1", self.instance.request["url"], "request_with_auth should not alter existing request")
        self.assertIn("key=oehhh", request["url"])
        self.assertNotIn(
            "key=oehhh", self.instance.request["url"],
            "request_with_auth should not alter existing request"
        )
        self.assertEqual({"Accept": "application/json", "Authorization": "Bearer oehhh"}, request["headers"])
        self.assertNotIn("Authorization", self.instance.request["headers"],
                         "request_without_auth should not alter existing request")
        self.assertEqual(request["data"], self.test_post_request["data"])

    def test_request_without_auth(self):
        self.instance.request = deepcopy(self.test_post_request)
        self.instance.request["url"] = self.test_post_request["url"] + "&auth=1&key=ahhh"
        self.instance.request["headers"].update({"Authorization": "Token ahhh"})
        request = self.instance.request_without_auth()
        self.assertNotIn("auth=1", request["url"])
        self.assertIn("auth=1", self.instance.request["url"], "request_without_auth should not alter existing request")
        self.assertNotIn("key=oehhh", request["url"])
        self.assertIn("key=ahhh", self.instance.request["url"],
                      "request_without_auth should not alter existing request")
        self.assertIn("key=ahhh", self.instance.request["url"],
                      "request_without_auth should not alter existing request")
        self.assertEqual({"Accept": "application/json"}, request["headers"])
        self.assertEqual(
            {"Accept": "application/json", "Authorization": "Token ahhh"},
            self.instance.request["headers"],
            "request_without_auth should not alter existing request"
        )
        self.assertEqual(request["data"], self.test_post_request["data"])

    def test_create_next_request(self):
        # Test with get
        instance = HttpResourceMock().get("next")
        request = instance.create_next_request()
        self.assertIsNotNone(request)
        self.assertIn("next=1", request["url"])
        self.assertNotIn("auth=1", instance.request["url"], "create_next_request should not alter existing request")
        # Test with post
        instance = HttpResourceMock().post(query="next")
        request = instance.create_next_request()
        self.assertIsNotNone(request)
        self.assertIn("next=1", request["url"])
        self.assertNotIn("auth=1", instance.request["url"], "create_next_request should not alter existing request")
        instance = HttpResourceMock().post(query="next", file="text-file.txt")
        request = instance.create_next_request()
        self.assertIsNotNone(request)
        self.assertIn("next=1", request["url"])
        self.assertNotIn("auth=1", instance.request["url"], "create_next_request should not alter existing request")
        # Test that None is returned when there is no continuation
        instance = HttpResourceMock().get("success")
        request = instance.create_next_request()
        self.assertIsNone(request)
        instance = HttpResourceMock().post(query="success")
        request = instance.create_next_request()
        self.assertIsNone(request)
        instance = HttpResourceMock().post(query="success", file="text-file.txt")
        request = instance.create_next_request()
        self.assertIsNone(request)

    def test_validate_get_request_args(self):
        # Make a new copy of GET_SCHEMA on test instance to not effect other tests
        self.instance.GET_SCHEMA = deepcopy(self.instance.GET_SCHEMA)
        # Valid
        try:
            self.instance.validate_request(self.test_get_request)
        except ValidationError:
            self.fail("validate_request raised for a valid request.")
        # Valid (JSON string)
        try:
            self.instance.validate_request(json.dumps(self.test_get_request))
        except ValidationError:
            self.fail("validate_request raised for a valid request using JSON string.")
        # Invalid
        invalid_request = deepcopy(self.test_get_request)
        invalid_request["args"] = ("en", "en", "test",)
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

    def test_validate_post_request_kwargs(self):
        # Make a new copy of GET_SCHEMA on test instance to not effect other tests
        self.instance.POST_SCHEMA = deepcopy(self.instance.POST_SCHEMA)
        # Valid
        try:
            self.instance.validate_request(self.test_post_request)
        except ValidationError:
            self.fail("validate_request raised for a valid request.")
        # Valid (JSON string)
        try:
            self.instance.validate_request(json.dumps(self.test_post_request))
        except ValidationError:
            self.fail("validate_request raised for a valid request using JSON string.")
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
        # Request dict
        self.instance.request = self.test_get_request
        self.instance.clean()
        self.assertEqual(self.instance.uri, "localhost:8000/en/?q=test")
        self.assertEqual(self.instance.data_hash, "")
        self.assertIsNone(self.instance.purge_at)
        # Request JSON
        self.instance.request = json.dumps(self.test_get_request)
        self.instance.clean()
        self.assertEqual(self.instance.uri, "localhost:8000/en/?q=test")
        self.assertEqual(self.instance.data_hash, "")
        self.assertIsNone(self.instance.purge_at)

    def test_clean_post(self):
        # Request dict
        self.instance.request = self.test_post_request
        self.instance.clean()
        self.assertEqual(self.instance.uri, "localhost:8000/en/?q=test")
        self.assertEqual(self.instance.data_hash, "c6ce96ff340b2fa4ead97ae01efa7fe20ca727bb")
        self.assertIsNone(self.instance.purge_at)
        # Request JSON
        self.instance.uri = None
        self.instance.data_hash = None
        self.instance.request = json.dumps(self.test_post_request)
        self.instance.clean()
        self.assertEqual(self.instance.uri, "localhost:8000/en/?q=test")
        self.assertEqual(self.instance.data_hash, "c6ce96ff340b2fa4ead97ae01efa7fe20ca727bb")
        self.assertIsNone(self.instance.purge_at)
        # Request dict, but using JSON as content type
        self.instance.uri = None
        self.instance.data_hash = None
        self.instance.request = deepcopy(self.test_post_request)
        self.instance.request["json"] = self.instance.request.pop("data")
        self.instance.clean()
        self.assertEqual(self.instance.uri, "localhost:8000/en/?q=test")
        self.assertEqual(self.instance.data_hash, "c6ce96ff340b2fa4ead97ae01efa7fe20ca727bb")
        self.assertIsNone(self.instance.purge_at)

    def test_user_agent(self):
        instance = HttpResourceMock(config={"user_agent": "DataScope (custom)"}).get("agent")
        self.assertTrue(instance.session.send.called)
        self.assertEqual(instance.head, self.content_type_header)
        self.assertEqual(instance.body, json.dumps(MOCK_DATA))
        self.assertEqual(instance.status, 200)
        self.assertFalse(instance.data_hash)
        self.assertEqual(instance.session.send.call_count, 1)
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
        mime_type, encoding = HttpResource.parse_content_type("text/html; charset=utf-8")
        self.assertEqual(mime_type, "text/html")
        self.assertEqual(encoding, "utf-8")
        mime_type, encoding = HttpResource.parse_content_type("text/html; charset=utf-16")
        self.assertEqual(mime_type, "text/html")
        self.assertEqual(encoding, "utf-16")
        mime_type, encoding = HttpResource.parse_content_type("text/plain; charset=latin-1")
        self.assertEqual(mime_type, "text/plain")
        self.assertEqual(encoding, "latin-1")
        mime_type, encoding = HttpResource.parse_content_type("text/html")
        self.assertEqual(mime_type, "text/html")
        self.assertEqual(encoding, "utf-8")
        mime_type, encoding = HttpResource.parse_content_type("text/plain")
        self.assertEqual(mime_type, "text/plain")
        self.assertEqual(encoding, "utf-8")
        mime_type, encoding = HttpResource.parse_content_type("text/html", default_encoding="utf-16")
        self.assertEqual(mime_type, "text/html")
        self.assertEqual(encoding, "utf-16")
        mime_type, encoding = HttpResource.parse_content_type("text/plain", default_encoding="latin-1")
        self.assertEqual(mime_type, "text/plain")
        self.assertEqual(encoding, "latin-1")
