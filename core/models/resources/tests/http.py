import json
from copy import deepcopy

from django.test import TestCase
from django.core.exceptions import ValidationError

from core.exceptions import DSHttpError50X, DSHttpError40X
from core.models.resources.http import HttpResource, HttpResourceMock
from core.utils.mocks import MOCK_DATA


class HttpResourceTestMixin(TestCase):

    def setUp(self):
        super(HttpResourceTestMixin, self).setUp()
        self.instance = self.get_test_instance()

    @staticmethod
    def get_test_instance():
        raise NotImplementedError()

    def test_data(self):
        # type only
        pass

    def test_parameters(self):
        self.assertIsInstance(self.instance.parameters(), dict)

    def test_auth_parameters(self):
        self.assertIsInstance(self.instance.auth_parameters(), dict)

    def test_next_parameters(self):
        self.assertIsInstance(self.instance.next_parameters(), dict)

    def test_make_request(self):
        test_url = "http://localhost:8000/test/"
        content_header = {
            "ContentType": "application/json"
        },
        self.instance.request = {
            "args": tuple(),
            "kwargs": {},
            "method": "get",
            "url": test_url,
            "headers": content_header,
            "data": {},
        }
        self.instance._make_request()

        args, kwargs = self.instance.session.get.call_args
        self.assertEqual(args[0], test_url)
        self.assertEqual(kwargs["headers"], content_header)

        self.assertEqual(self.instance.head, {"ContentType": "application/json"})
        self.assertEqual(self.instance.body, json.dumps(MOCK_DATA))
        self.assertEqual(self.instance.status, 200)

        self.instance.request = None
        try:
            self.instance._make_request()
            self.fail("_make_request should fail when self.request is not set.")
        except AssertionError:
            pass

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
            except DSHttpError50X:
                pass
            except Exception, exception:
                self.fail("Handle error throws wrong exception '{}' expecting 50X".format(exception))
        for status in statuses_40x:
            self.instance.status = status
            try:
                self.instance._handle_errors()
                self.fail("Handle error doesn't handle status {}".format(status))
            except DSHttpError40X:
                pass
            except Exception, exception:
                self.fail("Handle error throws wrong exception '{}' expecting 40X".format(exception))


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


class TestHttpResource(HttpResourceTestMixin, ConfigurationFieldTestMixin):

    fixtures = ['test-http-resource-mock']

    @staticmethod
    def get_test_instance():
        return HttpResourceMock()

    def fill_test_instance(self):
        self.instance.uri = "uri"
        self.instance.post_data = "12345"
        self.instance.head = {"json": "test"}
        self.instance.body = "response"
        self.instance.status = 200

    def setUp(self):
        super(TestHttpResource, self).setUp()
        self.test_request = {
            "args": ("en", "test",),
            "kwargs": {},
            "method": "get",
            "url": "http://localhost:8000/en/?q=test",
            "headers": {},
            "data": {},
        }

    def test_get(self):
        content_header = {
            "ContentType": "application/json"
        }
        # Make a new request
        instance = self.model().get("new")
        args, kwargs = instance.session.get.call_args
        self.assertEqual(args[0], "http://localhost:8000/en/?q=new&key=oehhh&auth=1")
        self.assertEqual(kwargs["headers"], content_header)
        self.assertEqual(instance.head, {"ContentType": "application/json"})
        self.assertEqual(instance.body, json.dumps(MOCK_DATA))
        self.assertEqual(instance.status, 200)
        # Load an existing request
        instance.session.get.reset_mock()
        instance = self.model().get("success")
        self.assertFalse(instance.session.get.called)
        self.assertEqual(instance.head, {"ContentType": "application/json"})
        self.assertEqual(instance.body, json.dumps(MOCK_DATA))
        self.assertEqual(instance.status, 200)
        # init, load -> retry
        # preset, new
        # preset, load
        # preset, load -> retry
        # invalid init
        # invalid preset
        pass

    def test_request_with_auth(self):
        pass

    def test_request_without_auth(self):
        pass

    def test_create_next_request(self):
        pass

    def test_validate_request_args(self):
        # Valid
        try:
            self.instance.validate_request(self.test_request)
        except ValidationError as ex:
            self.fail("validate_request raised for a valid request.")
        # Invalid
        invalid_request = deepcopy(self.test_request)
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
            self.instance.validate_request(self.test_request)
            self.fail("validate_request did not raise with invalid args for no schema.")
        except ValidationError:
            pass
        # Always valid schema
        self.instance.GET_SCHEMA["args"] = {}
        try:
            self.instance.validate_request(invalid_request)
        except ValidationError:
            self.fail("validate_request invalidated with a schema without restrictions.")

    def test_clean(self):
        pass