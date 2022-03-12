import subprocess
import string
import json
import jsonschema
from copy import copy
from jsonschema.exceptions import ValidationError as SchemaValidationError
from time import sleep

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.timezone import now
try:
    from django.db.models import JSONField
except ImportError:
    from django.contrib.postgres.fields import JSONField

from datagrowth import settings as datagrowth_settings
from datagrowth.resources.base import Resource
from datagrowth.exceptions import DGShellError, DGResourceDoesNotExist


class ShellResource(Resource):
    """
    You can extend from this base class to declare a ``Resource`` that gathers data from a any shell command.

    This class is a wrapper around the subprocess module and provides:

    * cached responses when retrieving data a second time

    The resource stores the stdin, stdout and stderr from commands in the database
    as well as an abstraction of the command.
    """

    # Getting data
    command = JSONField(default=None, null=True, blank=True)
    stdin = models.TextField(default=None, null=True, blank=True)

    # Storing data
    stdout = models.TextField(default=None, null=True, blank=True)
    stderr = models.TextField(default=None, null=True, blank=True)

    # Class constants that determine behavior
    CMD_TEMPLATE = []
    FLAGS = {}
    VARIABLES = {}
    DIRECTORY_SETTING = None
    CONTENT_TYPE = "text/plain"

    SCHEMA = {
        "arguments": {},
        "flags": {}
    }

    #######################################################
    # PUBLIC FUNCTIONALITY
    #######################################################
    # Call run to execute the command
    # Success and content are to handle the results
    # Override transform to manipulate command results

    def run(self, *args, **kwargs):
        """
        This method handles the gathering of data and updating the model based on the resource configuration.
        If the data has been retrieved before it will load the data from cache instead.
        Specify ``cache_only`` in your config if you want to prevent any execution of commands.
        The data might be missing in that case.

        Any arguments will be passed to ``CMD_TEMPLATE`` to format it.
        Any keyword arguments will be parsed into command flags by using the ``FLAGS`` attribute.
        The parsed flags will be inserted into ``CMD_TEMPLATE`` where ever the ``CMD_FLAGS`` value is present.

        :param args: get passed on to the command
        :param kwargs: get parsed into flags before being passed on to the command
        :return: self
        """

        if not self.command:
            self.command = self._create_command(*args, **kwargs)
            self.uri = self.uri_from_cmd(self.command.get("cmd"))
        else:
            self.validate_command(self.command)

        self.clean()  # sets self.uri
        resource = None
        try:
            resource = self.__class__.objects.get(uri=self.uri, stdin=self.stdin)
        except self.DoesNotExist:
            if self.config.cache_only:
                raise DGResourceDoesNotExist("Could not retrieve resource from cache", resource=self)
            resource = self

        if self.config.cache_only:
            return resource

        try:
            self.validate_command(resource.command)
        except ValidationError:
            if resource.id:
                resource.delete()
            resource = self

        if resource.success:
            return resource

        resource._run()
        resource.handle_errors()
        if self.interval_duration:
            sleep(self.interval_duration / 1000)
        return resource

    @property
    def success(self):
        """
        Returns True if exit code is 0 and there is some stdout
        """
        return self.status == 0 and bool(self.stdout)

    @property
    def content(self):
        """
        After a successful ``run`` call this method passes stdout from the command through the ``transform`` method.
        It then returns the value of the ``CONTENT_TYPE`` attribute as content type
        and whatever transform returns as data

        :return: content_type, data
        """
        if not self.success:
            return None, None
        return self.CONTENT_TYPE, self.transform(self.stdout)

    def transform(self, stdout):
        """
        Override this method for particular commands.
        It takes the stdout from the command and transforms it into useful output for other components.
        One use case could be to clean out log lines from the output.

        :param stdout: the stdout from the command
        :return: transformed stdout
        """
        return stdout

    def environment(self, *args, **kwargs):
        """
        You can specify environment variables for the command based on the input to ``run`` by overriding this method.
        The input from ``run`` is passed down to this method,
        based on this a dictionary should get returned containing the environment variables
        or None if no environment should be set.

        By default this method returns the ``VARIABLES`` attribute without making changes to it.

        :param args: arguments from the ``run`` command
        :param kwargs: keyword arguments from the ``run`` command
        :return: a dictionary with environment variables or None
        """
        if not self.VARIABLES:
            return None
        else:
            return self.VARIABLES

    def debug(self):
        """
        A method that prints to stdout the command that will get executed by the ``ShellResource``.
        This is mostly useful for debugging during development.
        """
        print(subprocess.list2cmdline(self.command.get("cmd", [])))

    #######################################################
    # CREATE COMMAND
    #######################################################
    # A set of methods to create a command dictionary
    # The values inside are passed to the subprocess library

    def variables(self, *args):
        """
        Parsers the input variables and returns a dictionary with an "input" key.
        This key contains a list of variables that will be used to format the ``CMD_TEMPLATE``.

        :return: (dict) a dictionary where the input variables are available under names
        """
        args = args or (self.command["args"] if self.command else tuple())
        return {
            "input": args
        }

    def _create_command(self, *args, **kwargs):
        self._validate_input(*args, **kwargs)

        # First we format the command template
        formatter = string.Formatter()
        arguments = iter(args)
        cmd = []
        for part in self.CMD_TEMPLATE:
            fields = formatter.parse(part)
            for literal_text, field_name, format_spec, conversion in fields:
                if field_name is not None:
                    part = part.format(next(arguments))
            cmd.append(part)

        # Then we set the flags
        flags = ""
        try:
            flags_index = cmd.index("CMD_FLAGS")
        except ValueError:
            flags_index = None
        if flags_index is not None:
            for key, value in kwargs.items():
                if key in self.FLAGS:
                    flags += " " + self.FLAGS[key] + str(value)
            flags = flags.lstrip()
            cmd[flags_index] = flags

        # Returning command
        command = {
            "args": args,
            "kwargs": kwargs,
            "cmd": cmd,
            "flags": flags
        }
        return self.validate_command(command, validate_input=False)

    def _validate_input(self, *args, **kwargs):
        args_schema = self.SCHEMA.get("arguments")
        kwargs_schema = self.SCHEMA.get("flags")
        if args_schema is None and len(args):
            raise ValidationError("Received arguments for command where there should be none.")
        if kwargs_schema is None and len(kwargs):
            raise ValidationError("Received keyword arguments for command where there should be none.")
        if args_schema:
            try:
                jsonschema.validate(list(args), args_schema)
            except SchemaValidationError as ex:
                raise ValidationError(
                    "{}: {}".format(self.__class__.__name__, str(ex))
                )
        if kwargs_schema:
            try:
                jsonschema.validate(kwargs, kwargs_schema)
            except SchemaValidationError as ex:
                raise ValidationError(
                    "{}: {}".format(self.__class__.__name__, str(ex))
                )

    def validate_command(self, command, validate_input=True):
        """
        Validates a dictionary that represents a command that the resource will run.

        It currently checks whether the current data (if any) is still valid or has expired.
        Apart from that it validates input which should adhere to
        the JSON schema defined in the ``SCHEMA`` attribute.

        :param command: (dict) the command dictionary
        :param validate_input: (bool) whether to validate input
        :return:
        """
        if self.purge_at is not None and self.purge_at <= now():
            raise ValidationError("Resource is no longer valid and will get purged")
        # Legacy HttpResource instances may have a JSON string as command
        # We parse that JSON to actual data here
        if isinstance(command, str):
            command = json.loads(command)
        # Internal asserts about the request
        assert isinstance(command, dict), \
            "Command should be a dictionary."
        assert isinstance(command["cmd"], list), \
            "Cmd should be a list that can be passed on to subprocess.run"
        if validate_input:
            self._validate_input(
                *command.get("args", tuple()),
                **command.get("kwargs", {})
            )
        # All is fine :)
        return command

    def clean_stdout(self, stdout):
        """
        This method decodes the stdout from the subprocess result to UTF-8.
        Override this method to do any further cleanup.

        :param stdout: (bytes) stdout from the command
        :return: (str) cleaned decoded output
        """
        return stdout.decode("utf-8").replace("\x00", "")

    def clean_stderr(self, stderr):
        """
        This method decodes the stderr from the subprocess result to UTF-8.
        Override this method to do any further cleanup.

        :param stderr: (bytes) stderr from the command
        :return: (str) cleaned decoded output
        """
        return stderr.decode("utf-8").replace("\x00", "")

    #######################################################
    # PROTECTED METHODS
    #######################################################
    # Some internal methods to execute the shell commands
    # Currently it wraps subprocess

    def _run(self):
        """
        Does the actual command execution based on the computed link
        Will set storage fields to returned values
        """

        assert self.command and isinstance(self.command, dict), \
            "Trying to run command before having a valid command dictionary."

        cmd = self.command.get("cmd")
        cwd = None
        env = self.environment(*self.command.get("args"), **self.command.get("kwargs"))
        if self.DIRECTORY_SETTING:
            cwd = getattr(datagrowth_settings, self.DIRECTORY_SETTING)
        results = subprocess.run(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=env
        )
        self._update_from_results(results)

    def _update_from_results(self, results):
        self.status = results.returncode
        self.stdout = self.clean_stdout(results.stdout)
        self.stderr = self.clean_stderr(results.stderr)

    def handle_errors(self):
        """
        Raises exceptions upon error statuses
        Override this method to raise exceptions for your own error states.
        By default it raises the ``DGShellError`` for any status other than 0.
        """
        if not self.success:
            class_name = self.__class__.__name__
            message = "{} > {} \n\n {}".format(class_name, self.status, self.stderr)
            raise DGShellError(message, resource=self)

    #######################################################
    # DJANGO MODEL
    #######################################################
    # Methods and properties to tweak Django

    def clean(self):
        # Legacy HttpResource instances may have a JSON string as command
        # We parse that JSON to actual data here
        if isinstance(self.command, str):
            self.command = json.loads(self.command)
        if self.command and not self.uri:
            self.uri = ShellResource.uri_from_cmd(self.command.get("cmd"))
        super().clean()

    #######################################################
    # CONVENIENCE
    #######################################################
    # Some static methods to provide standardization

    @staticmethod
    def uri_from_cmd(cmd):
        """
        Given a command list this method will sort that list, but keeps the first element as first element.
        That way a database lookup for a command will always return a command that logically match that command.
        Regardless of flag or argument order.
        At the same time similar commands will appear beneath each other in an overview.

        :param cmd: the command list as passed to subprocess.run to normalize to URI
        :return: a normalized URI suitable for lookups
        """
        cmd = copy(cmd)
        main = cmd.pop(0)
        cmd.sort()
        cmd.insert(0, main)
        return " ".join(cmd)

    class Meta:
        abstract = True
