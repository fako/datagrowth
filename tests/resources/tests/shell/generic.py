"""
This file tests the public interface to ShellResource and how a ShellResource should be used in practice.
Some core functionality shared by all derived classes of ShellResource gets tested in the core.py test module.
"""

import json
from unittest.mock import patch

from django.test import TestCase
from django.core.exceptions import ValidationError

from datagrowth import settings as datagrowth_settings
from datagrowth.resources import ShellResource
from datagrowth.exceptions import DGResourceDoesNotExist

from resources.models import ShellResourceMock
from resources.mocks.subprocess import SubprocessResult


class TestShellResourceInterface(TestCase):

    fixtures = ["test-shell-resource-mock"]

    def setUp(self):
        super().setUp()
        self.model = ShellResourceMock
        self.test_command = ["grep", "-R", "--context=5", "test", "."]
        self.test_command_2 = ["grep", "-R", "--context=3", "test", ".."]
        self.fail_command = ["grep", "-R", "--context=5", "fail", "."]
        self.test_command_dict = {
            "args": ("test", ".",),
            "kwargs": {"context": 5},
            "cmd": self.test_command,
            "flags": "--context=5"
        }

    def assert_call_args_run(self, call_args, expected_command):
        args, kwargs = call_args
        cmd = args[0]
        self.assertEqual(cmd, expected_command)
        self.assertEqual(kwargs["stdin"], -1)
        self.assertEqual(kwargs["stdout"], -1)
        self.assertEqual(kwargs["stderr"], -1)
        self.assertEqual(kwargs["env"], {"environment": "production"})
        self.assertEqual(kwargs["cwd"], datagrowth_settings.DATAGROWTH_MEDIA_ROOT)

    def test_http_resource_instance(self):
        # A basic check to assure that HttpResource "core" functionality gets checked for the class under test
        self.assertIsInstance(self.model(), ShellResource)

    @patch("datagrowth.resources.shell.generic.subprocess.run", return_value=SubprocessResult(0, b"out", b""))
    def test_run_command(self, subprocess_mock):
        # Make a new request and store it.
        instance = self.model().run("test", ".", context=5)
        self.assertIsNone(instance.id, "ShellResource used cache when it should have retrieved with requests")
        instance.save()
        self.assertEquals(subprocess_mock.call_count, 1)
        self.assert_call_args_run(subprocess_mock.call_args, self.test_command)
        self.assertEqual(instance.stdout, "out")
        self.assertEqual(instance.stderr, "")
        self.assertEqual(instance.status, 0)
        self.assertTrue(instance.id)
        # Make a new request from an existing command dictionary
        command = self.model().run("test", "..", context=3).command
        subprocess_mock.reset_mock()
        instance = self.model(command=command).run()
        self.assertIsNone(instance.id, "HttpResource used cache when it should have retrieved with requests")
        instance.save()
        self.assertEquals(subprocess_mock.call_count, 1)
        self.assert_call_args_run(subprocess_mock.call_args, self.test_command_2)
        self.assertEqual(instance.stdout, "out")
        self.assertEqual(instance.stderr, "")
        self.assertEqual(instance.status, 0)
        self.assertTrue(instance.id)

    @patch("datagrowth.resources.shell.generic.subprocess.run", return_value=SubprocessResult(0, b"out", b""))
    def test_get_success(self, subprocess_mock):
        # Load an existing command
        instance = self.model().run("success", ".", context=5)
        self.assertFalse(subprocess_mock.called)
        self.assertEqual(instance.stdout, "out")
        self.assertEqual(instance.stderr, "")
        self.assertEqual(instance.status, 0)
        self.assertTrue(instance.id)
        # Load an existing resource from its command
        command = instance.command
        instance = self.model(command=command).run()
        self.assertFalse(subprocess_mock.called)
        self.assertEqual(instance.stdout, "out")
        self.assertEqual(instance.stderr, "")
        self.assertEqual(instance.status, 0)
        self.assertTrue(instance.id)

    @patch("datagrowth.resources.shell.generic.subprocess.run", return_value=SubprocessResult(0, b"out", b""))
    def test_get_retry(self, subprocess_mock):
        # Load and retry an existing command
        instance = self.model().run("fail", ".", context=5)
        self.assertEquals(subprocess_mock.call_count, 1)
        self.assert_call_args_run(subprocess_mock.call_args, self.fail_command)
        self.assertEqual(instance.stdout, "out")
        self.assertEqual(instance.stderr, "")
        self.assertEqual(instance.status, 0)
        self.assertTrue(instance.id)
        # Load an existing resource from its command
        subprocess_mock.reset_mock()
        command = instance.command
        instance = self.model(command=command).run()
        self.assertEquals(subprocess_mock.call_count, 1)
        self.assert_call_args_run(subprocess_mock.call_args, self.fail_command)
        self.assertEqual(instance.stdout, "out")
        self.assertEqual(instance.stderr, "")
        self.assertEqual(instance.status, 0)
        self.assertTrue(instance.id)

    def test_get_invalid(self):
        # Invalid invoke of run
        try:
            self.model().run()
            self.fail("Run did not raise a validation exception when invoked with invalid arguments.")
        except ValidationError:
            pass
        # Invalid command preset
        self.test_command_dict["args"] = tuple()
        try:
            self.model(command=self.test_command_dict).run()
            self.fail("Run did not raise a validation exception when confronted with an invalid preset command.")
        except ValidationError:
            pass

    @patch("datagrowth.resources.shell.generic.subprocess.run", return_value=SubprocessResult(0, b"out", b""))
    def test_get_cache_only(self, subprocess_mock):
        # Load an existing resource from cache
        instance = self.model(config={"cache_only": True}).run("success", ".", context=5)
        self.assertFalse(subprocess_mock.called)
        self.assertEqual(instance.status, 0)
        self.assertEqual(instance.stdout, "out")
        self.assertEqual(instance.stderr, "")
        self.assertTrue(instance.id)
        # Load an existing resource from cache by its request
        command = instance.command
        instance = self.model(command=command, config={"cache_only": True}).run()
        self.assertFalse(subprocess_mock.called)
        self.assertEqual(instance.status, 0)
        self.assertEqual(instance.stdout, "out")
        self.assertEqual(instance.stderr, "")
        self.assertTrue(instance.id)
        # Load a failed resource from cache
        instance = self.model(config={"cache_only": True}).run("fail", ".", context=5)
        self.assertFalse(subprocess_mock.called)
        self.assertEqual(instance.status, 1)
        self.assertEqual(instance.stdout, "")
        self.assertEqual(instance.stderr, "err")
        self.assertTrue(instance.id)
        # Fail to load from cache
        try:
            self.model(config={"cache_only": True}).run("new", ".", context=5)
            self.fail("Missing resource in cache did not raise an exception")
        except DGResourceDoesNotExist:
            pass
