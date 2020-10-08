"""
This file tests some core functionality by testing with ShellResourceMock instances.
However these tests are assumed to be important for all derived classes of ShellResource.
In that sense it is testing the "core" of ShellResource through ShellResourceMock.

The tests of the actual interface to ShellResource and how a ShellResource should be used in practice
is present in the generic.py test module.
"""

from copy import deepcopy
from unittest.mock import patch

from django.core.exceptions import ValidationError

from datagrowth import settings as datagrowth_settings
from datagrowth.exceptions import DGShellError
from datagrowth.resources import ShellResource
from datagrowth.configuration.types import ConfigurationType

from resources.models import ShellResourceMock
from resources.tests.base import ResourceTestMixin
from resources.mocks.subprocess import SubprocessResult


class TestShellResource(ResourceTestMixin):

    fixtures = ["test-http-resource-mock"]

    @staticmethod
    def get_test_instance():
        return ShellResourceMock()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        instance = cls.get_test_instance()
        cls.DEFAULT_CONTENT_TYPE = instance.__class__.CONTENT_TYPE
        cls.DEFAULT_VARIABLES = instance.__class__.VARIABLES
        cls.DEFAULT_TRANSFORM = instance.__class__.transform

    def setUp(self):
        self.instance = self.get_test_instance()
        self.test_command = ["grep", "-R", "--context=5", "test", "."]
        self.test_command_dict = {
            "args": ("test", ".",),
            "kwargs": {"context": 5},
            "cmd": self.test_command,
            "flags": "--context=5"
        }

    def tearDown(self):
        super().tearDown()
        ShellResourceMock.CONTENT_TYPE = self.DEFAULT_CONTENT_TYPE
        ShellResourceMock.VARIABLES = self.DEFAULT_VARIABLES
        ShellResourceMock.transform = self.DEFAULT_TRANSFORM

    def test_configuration(self):
        self.assertIsInstance(self.instance.config, ConfigurationType)

    def test_content(self):
        test_result = "command result"
        # Test access when request is missing
        content_type, data = self.instance.content
        self.assertIsNone(content_type)
        self.assertIsNone(data)
        # Test when request was made
        self.instance.stdout = test_result
        content_type, data = self.instance.content
        self.assertEqual(content_type, "text/plain")
        self.assertEqual(data, test_result)
        # Set different content type
        self.instance.CONTENT_TYPE = "application/json"
        content_type, data = self.instance.content
        self.assertEqual(content_type, "application/json")
        self.assertEqual(data, test_result)
        self.instance.transform = lambda stdout: stdout.replace("result", "rezult")
        content_type, data = self.instance.content
        self.assertEqual(content_type, "application/json")
        self.assertEqual(data, "command rezult")

    def test_environment(self):
        self.assertIsInstance(self.instance.environment(), dict)
        self.instance.VARIABLES = {}
        self.assertIsNone(self.instance.environment())

    @patch("datagrowth.resources.shell.generic.subprocess.run", return_value=SubprocessResult(0, b"out", b""))
    def test_variables(self, run_mock):
        # Variables with explicit input
        variables = self.instance.variables("arg1", "arg2")
        self.assertIsInstance(variables, dict)
        self.assertIn("input", variables)
        self.assertIn("dir", variables)
        self.assertEquals(variables["input"], ("arg1", "arg2"))
        self.assertEquals(variables["dir"], "arg2")
        # Variables without input
        variables = self.instance.variables()
        self.assertIsInstance(variables, dict)
        self.assertIn("input", variables)
        self.assertIn("dir", variables)
        self.assertEquals(variables["input"], tuple())
        self.assertIsNone(variables["dir"])
        # Variables with input through run
        self.instance.run("test", context=5)
        variables = self.instance.variables()
        self.assertIn("input", variables)
        self.assertIn("dir", variables)
        self.assertEquals(variables["input"], ("test", ".",))
        self.assertEquals(variables["dir"], ".")

    @patch("datagrowth.resources.shell.generic.subprocess.run", return_value=SubprocessResult(0, b"out", b"err"))
    def test_run_command_core(self, subprocess_mock):
        test_command = ["grep", "-R", "--context=5", "test", "."]
        self.instance.command = {
            "args": ("test", ".",),
            "kwargs": {"context": 5},
            "cmd": test_command,
            "flags": "--context=5"
        }
        self.instance._run()
        # See if request was made properly
        self.assertEquals(subprocess_mock.call_count, 1)
        args, kwargs = subprocess_mock.call_args
        cmd = args[0]
        self.assertEqual(cmd, test_command)
        self.assertEqual(kwargs["stdin"], -1)
        self.assertEqual(kwargs["stdout"], -1)
        self.assertEqual(kwargs["stderr"], -1)
        self.assertEqual(kwargs["env"], {"environment": "production"})
        self.assertEqual(kwargs["cwd"], datagrowth_settings.DATAGROWTH_MEDIA_ROOT)
        # Make sure that response fields are set to something and do not remain None
        self.assertEqual(self.instance.stdout, "out")
        self.assertEqual(self.instance.stderr, "err")
        self.assertEqual(self.instance.status, 0)

    def test_run_command_core_wrong(self):
        self.instance.command = None
        try:
            self.instance._run()
            self.fail("_run should fail when self.command is not set.")
        except AssertionError:
            pass
        self.instance.command = ["grep", "test", "."]
        try:
            self.instance._run()
            self.fail("_run should fail when self.command is not a dictionary.")
        except AssertionError:
            pass

    def test_create_command(self):
        command = self.instance._create_command("test", ".", context=5)
        self.assertEqual(command,  {
            "args": ("test", ".",),
            "kwargs": {"context": 5},
            "cmd": ["grep", "-R", "--context=5", "test", "."],
            "flags": "--context=5"
        })

    def test_success(self):
        self.assertFalse(self.instance.success)
        self.instance.stdout = "0"
        self.assertTrue(self.instance.success)
        self.instance.status = 1
        self.assertFalse(self.instance.success)
        self.instance.status = 0
        self.assertTrue(self.instance.success)

    def test_handle_errors(self):
        self.assertFalse(self.instance.success)
        try:
            self.instance.handle_errors()
            self.fail("Handle error doesn't raise on error")
        except DGShellError as exc:
            self.assertIsInstance(exc.resource, ShellResource)
            self.assertEqual(exc.resource.status, 0)
            self.assertIsNone(exc.resource.stdout)
        except Exception as exception:
            self.fail("Handle error throws wrong exception '{}' expecting ShellError".format(exception))

    def test_uri_from_cmd(self):
        uri = ShellResource.uri_from_cmd(["grep", "-R", "--context=5", "test", "."])
        self.assertEqual(uri, "grep --context=5 -R . test")

    def test_validate_command_args(self):
        # Make a new copy of GET_SCHEMA on test instance to not effect other tests
        self.instance.SCHEMA = deepcopy(self.instance.SCHEMA)
        # Valid
        try:
            self.instance.validate_command(self.test_command_dict)
        except ValidationError:
            self.fail("validate_command raised for a valid request.")
        # Invalid
        invalid_request = deepcopy(self.test_command_dict)
        invalid_request["args"] = (".", "test", "/")
        try:
            self.instance.validate_command(invalid_request)
            self.fail("validate_command did not raise with invalid args for schema.")
        except ValidationError:
            pass
        invalid_request["args"] = tuple()
        try:
            self.instance.validate_command(invalid_request)
            self.fail("validate_command did not raise with invalid args for schema.")
        except ValidationError:
            pass
        # No schema
        self.instance.SCHEMA["arguments"] = None
        try:
            self.instance.validate_command(self.test_command_dict)
            self.fail("validate_command did not raise with invalid args for no schema.")
        except ValidationError:
            pass
        # Always valid schema
        self.instance.SCHEMA["arguments"] = {}
        try:
            self.instance.validate_command(invalid_request)
        except ValidationError:
            self.fail("validate_command invalidated with a schema without restrictions.")

    def test_clean_results(self):
        # Simple cleaning
        out = self.instance.clean_stdout(b"out")
        self.assertEqual(out, "out")
        err = self.instance.clean_stdout(b"err")
        self.assertEqual(err, "err")
        # Cleaning with some challanging bytes
        out = self.instance.clean_stdout(b"out\x00")
        self.assertEqual(out, "out\uFFFD")
        err = self.instance.clean_stdout(b"err\x00")
        self.assertEqual(err, "err\uFFFD")
        # Cleaned results should always be able to save a Resource
        self.instance.uri = "test-clean-results"
        self.instance.stdout = out
        self.instance.stderr = err
        self.instance.save()
