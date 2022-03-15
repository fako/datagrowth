import os
import re
import hashlib
import json
from copy import copy, deepcopy
from urllib.parse import urlencode
from time import sleep

import requests
import jsonschema
from jsonschema.exceptions import ValidationError as SchemaValidationError
from urlobject import URLObject
from bs4 import BeautifulSoup

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.timezone import now
try:
    from django.db.models import JSONField
except ImportError:
    from django.contrib.postgres.fields import JSONField

from datagrowth import settings as datagrowth_settings
from datagrowth.resources.base import Resource
from datagrowth.exceptions import DGHttpError50X, DGHttpError40X, DGResourceDoesNotExist
from datagrowth.utils import is_json_mimetype


class HttpResource(Resource):
    """
    You can extend from this base class to declare a ``Resource`` that gathers data from a HTTP(S) source.
    For instance websites and (REST)API's

    This class is a wrapper around the requests library and provides:

    * easy follow up of continuation URL's in responses
    * handle authentication through Datagrowth configs
    * cached responses when retrieving data a second time

    Response headers, body and status get stored in the database as well as an abstraction of the request.
    Any authentication data gets stripped before storage in the database.
    """

    # Identification
    data_hash = models.CharField(max_length=255, db_index=True, default="", blank=True)

    # Getting data
    request = JSONField(default=None, null=True, blank=True)

    # Storing data
    head = JSONField(default=dict)
    body = models.TextField(default=None, null=True, blank=True)

    # Class constants that determine behavior
    URI_TEMPLATE = ""
    PARAMETERS = {}
    DATA = {}
    HEADERS = {}
    FILE_DATA_KEYS = []
    GET_SCHEMA = {
        "args": {},
        "kwargs": {}
    }
    POST_SCHEMA = {
        "args": {},
        "kwargs": {}
    }

    #######################################################
    # PUBLIC FUNCTIONALITY
    #######################################################
    # The get and post methods are the ways to interact
    # with the external resource.
    # Success and content are convenient to handle the results

    def send(self, method, *args, **kwargs):
        """
        This method handles the gathering of data and updating the model based on the resource configuration.
        If the data has been retrieved before it will load the data from cache instead.
        Specify ``cache_only`` in your config if you want to prevent any HTTP requests.
        The data might be missing in that case.

        You must specify the method that the resource will be using to get the data.
        Currently this can be the "get" and "post" HTTP verbs.

        Any arguments will be passed to ``URI_TEMPLATE`` to format it.
        Any keyword arguments will be passed as a data dict to the request.
        If a keyword is listed in the ``FILE_DATA_KEYS`` attribute on a HttpResource,
        then the value of that argument is expected to be a file path relative to the ``DATAGROWTH_MEDIA_ROOT``.
        The value of that keyword will be replaced with the file before making the request.

        :param method: "get" or "post" depending on which request you want your resource to execute
        :param args: arguments that will get merged into the ``URI_TEMPLATE``
        :param kwargs: keywords arguments that will get send as data
        :return: HttpResource
        """
        if not self.request:
            self.request = self._create_request(method, *args, **kwargs)
            self.uri = self.uri_from_url(self.request.get("url"))
            self.data_hash = self.hash_from_data(
                self.request.get(HttpResource._get_data_key(self.request))
            )
        else:
            self.validate_request(self.request)

        self.clean()  # sets self.uri and self.data_hash based on request

        try:
            resource = self.__class__.objects.get(uri=self.uri, data_hash=self.data_hash)
        except self.DoesNotExist:
            if self.config.cache_only:
                raise DGResourceDoesNotExist("Could not retrieve resource from cache", resource=self)
            resource = self

        if self.config.cache_only:
            return resource

        try:
            self.validate_request(resource.request)
        except ValidationError:
            if resource.id:
                resource.delete()
            resource = self

        if resource.success:
            return resource

        resource.request = resource.request_with_auth()
        resource._send()
        resource.handle_errors()
        if self.interval_duration:
            sleep(self.interval_duration / 1000)
        return resource

    def get(self, *args, **kwargs):
        """
        This method calls ``send`` with "get" as a method. See the ``send`` method for more information.

        :param args: arguments that will get merged into the URI_TEMPLATE
        :param kwargs: keywords arguments that will get send as data
        :return: HttpResource
        """
        return self.send("get", *args, **kwargs)

    def post(self, *args, **kwargs):
        """
        This method calls ``send`` with "post" as a method. See the ``send`` method for more information.

        :param args: arguments that will get merged into the URI_TEMPLATE
        :param kwargs: keywords arguments that will get send as data
        :return: HttpResource
        """
        return self.send("post", *args, **kwargs)

    @property
    def success(self):
        """
        Returns True if status is within HTTP success range

        :return: Boolean
        """
        return self.status is not None and 200 <= self.status < 209

    @property
    def content(self):
        """
        After a successful ``get`` or ``post`` call this method reads the ContentType header from the HTTP response.
        Depending on the MIME type it will return the content type and the parsed data.

        * For a ContentType of application/json data will be a python structure
        * For a ContentType of text/html or text/xml data will be a BeautifulSoup instance

        Any other ContentType will result in None.
        You are encouraged to overextend ``HttpResource`` to handle your own data types.

        :return: content_type, data
        """
        if self.success:
            content_type = self.head.get("content-type", "unknown/unknown").split(';')[0]
            if is_json_mimetype(content_type):
                return content_type, json.loads(self.body)
            elif content_type == "text/html":
                return content_type, BeautifulSoup(self.body, "html5lib")
            elif content_type == "text/xml" or content_type == "application/xml":
                return content_type, BeautifulSoup(self.body, "lxml")
            else:
                return content_type, None
        return None, None

    #######################################################
    # CREATE REQUEST
    #######################################################
    # A set of methods to create a request dictionary
    # The values inside are passed to the requests library
    # Override parameters method to set dynamic parameters

    def _create_request(self, method, *args, **kwargs):
        self._validate_input(method, *args, **kwargs)
        data = self.data(**kwargs) if not method == "get" else None
        headers = requests.utils.default_headers()
        headers["User-Agent"] = "{}; {}".format(self.config.user_agent, headers["User-Agent"])
        headers.update(self.headers())
        request = {
            "args": args,
            "kwargs": kwargs,
            "method": method,
            "url": self._create_url(*args),
            "headers": dict(headers)
        }
        data_key = self._get_data_key(request, headers)
        request[data_key] = data
        return self.validate_request(request, validate_input=False)

    def _create_url(self, *args):
        url_template = copy(self.URI_TEMPLATE)
        variables = self.variables(*args)
        url = URLObject(url_template.format(*variables["url"]))
        params = url.query.dict
        params.update(self.parameters(**variables))
        url = url.set_query_params(params)
        return str(url)

    def headers(self):
        """
        Returns the dictionary that should be used as headers for the request the resource will make.
        By default this is the dictionary from the ``HEADERS`` attribute.

        :return: (dict) a dictionary representing HTTP headers
        """
        return self.HEADERS

    def parameters(self, **kwargs):
        """
        Returns the dictionary that should be used as HTTP query parameters for the request the resource will make.
        By default this is the dictionary from the ``PARAMETERS`` attribute.

        You may need to override this method. It will receive the return value of the variables method as kwargs.

        :param kwargs: variables returned by the variables method (ignored by default)
        :return: (dict) a dictionary representing HTTP query parameters
        """
        return self.PARAMETERS

    def data(self, **kwargs):
        """
        Returns the dictionary that will be used as HTTP body for the request the resource will make.
        By default this is the dictionary from the ``DATA`` attribute
        updated with the kwargs from the input from the ``send`` method.

        :param kwargs: keyword arguments from the input
        :return:
        """
        data = dict(self.DATA)
        data.update(**kwargs)
        return data

    def variables(self, *args):
        """
        Parsers the input variables and returns a dictionary with a "url" key.
        This key contains a list of variables that will be used to format the ``URI_TEMPLATE``.

        :return: (dict) a dictionary where the input variables are available under names
        """
        args = args or (self.request.get("args") if self.request else tuple())
        return {
            "url": args
        }

    def validate_request(self, request, validate_input=True):
        """
        Validates a dictionary that represents a request that the resource will make.
        Currently it checks the method, which should be "get" or "post"
        and whether the current data (if any) is still valid or has expired.
        Apart from that it validates input which should adhere to
        the JSON schema defined in the ``GET_SCHEMA`` or ``POST_SCHEMA`` attributes

        :param request: (dict) the request dictionary
        :param validate_input: (bool) whether to validate input
        :return:
        """
        if self.purge_at is not None and self.purge_at <= now():
            raise ValidationError("Resource is no longer valid and will get purged")
        # Legacy HttpResource instances may have a JSON string as request
        # We parse that JSON to actual data here
        if isinstance(request, str):
            request = json.loads(request)
        # Internal asserts about the request
        assert isinstance(request, dict), "Request should be a dictionary."
        method = request.get("method")
        assert method, "Method should not be falsy."
        assert method in ["get", "post"], \
            "{} is not a supported resource method.".format(request.get("method"))  # FEATURE: allow all methods
        if validate_input:
            self._validate_input(
                method,
                *request.get("args", tuple()),
                **request.get("kwargs", {})
            )
        # All is fine :)
        return request

    def _validate_input(self, method, *args, **kwargs):
        """
        Will validate the args and kwargs against the JSON schema set on ``GET_SCHEMA`` or ``POST_SCHEMA``,
        depending on the HTTP method used.

        :param method: the HTTP method to validate
        :param args: arguments to validate
        :param kwargs: keyword arguments to validate
        :return:
        """
        schemas = self.GET_SCHEMA if method == "get" else self.POST_SCHEMA  # FEATURE: allow all methods
        args_schema = schemas.get("args")
        kwargs_schema = schemas.get("kwargs")
        if args_schema is None and len(args):
            raise ValidationError("Received arguments for request where there should be none.")
        if kwargs_schema is None and len(kwargs):
            raise ValidationError("Received keyword arguments for request where there should be none.")
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

    def _format_data(self, data):
        """
        Will replace any keys that are present in data and the ``FILE_DATA_KEYS`` class attribute with file descriptors.
        The values of any key is presumed to be a path to a file relative to the ``DATAGROWTH_MEDIA_ROOT``.

        :param data: (dict) data where some file paths may need to be replaced with actual files
        :return: (dict) the formatted data
        """
        if data is None:
            return None, None
        files = {}
        for file_key in self.FILE_DATA_KEYS:
            relative_path = data.get(file_key, None)
            if relative_path:
                file_path = os.path.join(datagrowth_settings.DATAGROWTH_MEDIA_ROOT, relative_path)
                files[file_key] = open(file_path, "rb")
        data = {key: value for key, value in data.items() if key not in files}  # data copy without "files"
        files = files or None
        return data, files

    #######################################################
    # AUTH LOGIC
    #######################################################
    # Methods to enable auth for the resource.
    # Override auth_parameters to provide authentication.

    def auth_headers(self):
        """
        Returns the dictionary that should be used as authentication headers for the request the resource will make.
        Override this method in your own class to add authentication.
        By default this method returns an empty dictionary meaning there are no authentication headers.

        :return: (dict) dictionary with headers to add to requests
        """
        return {}

    def auth_parameters(self):
        """
        Returns the dictionary that should be used as authentication parameters for the request the resource will make.
        Override this method in your own class to add authentication.
        By default this method returns an empty dictionary meaning there are no authentication parameters.

        :return: (dict) dictionary with parameters to add to requests
        """
        return {}

    def request_with_auth(self):
        """
        Get the ``request`` that this resource will make with authentication headers and parameters added.
        Override ``auth_headers`` and/or ``auth_parameters`` to provide the headers and/or parameters.

        :return: (dict) a copy of the ``request`` dictionary with authentication added
        """
        url = URLObject(self.request.get("url"))
        params = url.query.dict
        params.update(self.auth_parameters())
        url = url.set_query_params(params)
        request = deepcopy(self.request)
        request["url"] = str(url)
        request["headers"].update(self.auth_headers())
        return request

    def request_without_auth(self):
        """
        Get the ``request`` that this resource will make with authentication headers and parameters from
        ``auth_headers`` and ``auth_parameters`` removed.

        :return: (dict) a copy of the ``request`` dictionary with authentication removed
        """
        url = URLObject(self.request.get("url"))
        url = url.del_query_params(self.auth_parameters())
        request = deepcopy(self.request)
        request["url"] = str(url)
        for key in self.auth_headers().keys():
            if key in request["headers"]:
                del request["headers"][key]
        return request

    #######################################################
    # NEXT LOGIC
    #######################################################
    # Methods to act on continuation for a resource
    # Override next_parameters to provide auto continuation

    def next_parameters(self):
        """
        Returns the dictionary that should be used as HTTP query parameters
        for the continuation request a resource can make.
        By default this is an empty dictionary.
        Override this method and return the correct parameters based on the ``content`` of the resource.

        :return: (dict) a dictionary representing HTTP continuation query parameters
        """
        return {}

    def create_next_request(self):
        """
        Creates and returns a dictionary that represents a continuation request.
        Often a source will indicate how to continue gather more data.
        By overriding the ``next_parameters`` developers can indicate how continuation requests can be made.
        Calling this method will build a new request using these parameters.

        :return: (dict) a dictionary representing a continuation request to be made
        """
        if not self.success or not self.next_parameters():
            return None
        url = URLObject(self.request.get("url"))
        params = url.query.dict
        params.update(self.next_parameters())
        url = url.set_query_params(params)
        request = deepcopy(self.request)
        request["url"] = str(url)
        return request

    #######################################################
    # PROTECTED METHODS
    #######################################################
    # Some internal methods for the get and post methods.

    def _send(self):
        """
        Does a get or post on the computed link
        Will set storage fields to returned values
        """
        assert self.request and isinstance(self.request, dict), \
            "Trying to make request before having a valid request dictionary."

        method = self.request.get("method")
        form_data = self.request.get("data") if not method == "get" else None
        form_data, files = self._format_data(form_data)
        json_data = self.request.get("json") if not method == "get" else None

        request = requests.Request(
            method=method,
            url=self.request.get("url"),
            headers=self.request.get("headers"),
            data=form_data,
            json=json_data,
            files=files
        )
        preq = self.session.prepare_request(request)

        for backoff_delay in [0] + self.config.backoff_delays:
            sleep(backoff_delay)
            try:
                response = self.session.send(
                    preq,
                    proxies=datagrowth_settings.DATAGROWTH_REQUESTS_PROXIES,
                    verify=datagrowth_settings.DATAGROWTH_REQUESTS_VERIFY,
                    timeout=self.timeout
                )
                self._update_from_results(response)
            except requests.exceptions.SSLError:
                self.set_error(496, connection_error=True)
            except requests.Timeout:
                self.set_error(504, connection_error=True)
            except (requests.ConnectionError, IOError):
                self.set_error(502, connection_error=True)
            except UnicodeDecodeError:
                self.set_error(600, connection_error=True)
            # Checks the status to see if we need to backoff from the server/connection or not
            self.request["backoff_delay"] = backoff_delay if backoff_delay else False
            if self.status not in [420, 429, 502, 503, 504]:
                break


    def _update_from_results(self, response):
        self.head = dict(response.headers.lower_items())
        self.status = response.status_code
        self.body = response.content if isinstance(response.content, str) else \
            response.content.decode("utf-8", "replace")

    def handle_errors(self):
        """
        Raises exceptions upon error statuses
        Override this method to raise exceptions for your own error states.
        By default it raises the ``DGHttpError40X`` and ``DGHttpError50X`` exceptions for statuses.
        """
        class_name = self.__class__.__name__
        if self.status >= 500:
            message = "{} > {} \n\n {}".format(class_name, self.status, self.body)
            raise DGHttpError50X(message, resource=self)
        elif self.status >= 400:
            message = "{} > {} \n\n {}".format(class_name, self.status, self.body)
            raise DGHttpError40X(message, resource=self)
        else:
            return True

    @staticmethod
    def _get_data_key(request, headers=None):
        """
        This method returns which key should be used when sending data through the requests library.
        A JSON request requires the "json" key while other requests require "data".

        :param request: (dict) a dictionary representing a request
        :param headers: (dict) a dictionary representing request headers
        :return: key to use when passing data to the requests library
        """
        if "data" in request:
            return "data"
        elif "json" in request:
            return "json"
        elif headers:
            return "json" if headers.get("Content-Type") == "application/json" else "data"
        raise AssertionError("Could not determine data_key for request {} or headers {}".format(request, headers))

    #######################################################
    # DJANGO MODEL
    #######################################################
    # Methods and properties to tweak Django

    def __init__(self, *args, **kwargs):
        self.session = kwargs.pop("session", requests.Session())
        self.timeout = kwargs.pop("timeout", 30)
        super(HttpResource, self).__init__(*args, **kwargs)

    def clean(self):
        # Legacy HttpResource instances may have a JSON string as request and head
        # We parse that JSON to actual data here
        if isinstance(self.request, str):
            self.request = json.loads(self.request)
        if isinstance(self.head, str):
            self.head = json.loads(self.head)
        # Actual cleaning implementation
        if self.request and not self.uri:
            uri_request = self.request_without_auth()
            self.uri = self.uri_from_url(uri_request.get("url"))
        if self.request and not self.data_hash:
            uri_request = self.request_without_auth()
            data_key = HttpResource._get_data_key(uri_request)
            self.data_hash = self.hash_from_data(uri_request.get(data_key))
        super().clean()

    #######################################################
    # CONVENIENCE
    #######################################################
    # Some static methods to provide standardization

    @staticmethod
    def uri_from_url(url):
        """
        Given a URL this method will strip the protocol and sort the parameters.
        That way a database lookup for a URL will always return URL's that logically match that URL.

        :param url: the URL to normalize to URI
        :return: a normalized URI suitable for lookups
        """
        url = URLObject(url)
        params = sorted(url.query.dict.items(), key=lambda item: item[0])
        url = url.with_query(urlencode(params))
        return str(url).replace(url.scheme + "://", "")

    @staticmethod
    def hash_from_data(data):
        """
        Given a dictionary will recursively sort and JSON dump the keys and values of that dictionary.
        The end result is given to SHA-1 to create a hash, that is unique for that data.
        This hash can be used for a database lookup to find earlier requests that send the same data.

        :param data: (dict) a dictionary of the data to be hashed
        :return: the hash of the data
        """
        if not data:
            return ""

        payload = []
        for key, value in data.items():
            if not isinstance(value, dict):
                payload.append((key, value))
            else:
                payload.append((key, HttpResource.hash_from_data(value)))

        payload.sort(key=lambda item: item[0])
        hash_payload = json.dumps(payload).encode("utf-8")

        hsh = hashlib.sha1()
        hsh.update(hash_payload)
        return hsh.hexdigest()

    @staticmethod
    def parse_content_type(content_type, default_encoding="utf-8"):
        """
        Given a HTTP ContentType header will return the mime type and the encoding.
        If no encoding is found the default encoding gets returned.

        :param content_type: (str) the HTTP ContentType header
        :param default_encoding: (str) the default encoding when
        :return: mime_type, encoding
        """
        match = re.match(
            "(?P<mime_type>[A-Za-z]+/[A-Za-z]+);? ?(charset=(?P<encoding>[A-Za-z0-9\-]+))?",
            content_type
        )
        if match is None:
            raise ValueError("Could not parse content_type")
        return match.group("mime_type"), match.group("encoding") or default_encoding

    def set_error(self, status, connection_error=False):
        """
        Sets the given status on the HttpResource.
        When dealing with connection_errors it sets valid defaults.

        :param status: (int) the error status from the response
        :param connection_error: (bool) whether the error occurred during a connection error
        :return:
        """
        if connection_error:
            self.head = {}
            self.body = ""
        self.status = status

    class Meta:
        abstract = True


class URLResource(HttpResource):
    """
    Sometimes you don't want to build a URI through the ``URI_TEMPLATE``,
    because you have a URL, where data should be retrieved from immediately.
    For this use case the ``URLResource`` is very suitable.
    Just pass the URL as a first argument to either ``get`` or ``post`` and the request will be made.

    Only full URL's with protocol are excepted as an argument.
    And note that it is not possible to adjust the parameters through the ``parameters`` method,
    because it is assumed that all parameters are part of the URL given to ``get`` or ``post``.
    """

    PARAMETERS = None

    GET_SCHEMA = {
        "args": {
            "type": "array",
            "items": [
                {
                    "type": "string",
                    "pattern": "^http"
                }
            ],
            "minItems": 1,
            "additionalItems": False
        }
    }
    POST_SCHEMA = {
        "args": {
            "type": "array",
            "items": [
                {
                    "type": "string",
                    "pattern": "^http"
                }
            ],
            "minItems": 1,
            "additionalItems": False
        },
        "kwargs": {}
    }

    def _create_url(self, *args):
        parameters = self.parameters()
        assert parameters is None, "Parameters got specified for the URLResource, but these get ignored"
        return args[0]

    class Meta:
        abstract = True


class MicroServiceResource(HttpResource):

    CONFIG_NAMESPACE = "micro_service"

    MICRO_SERVICE = None

    URI_TEMPLATE = "{}://{}{}"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert self.MICRO_SERVICE is not None, \
            "You should specify a micro service name under the MICRO_SERVICE attribute"
        self.connection = self.config.connections.get(self.MICRO_SERVICE, None)
        assert self.connection is not None, \
            '"{}" is an unknown micro service in the "connections" configuration. ' \
            'Is it added through register_defaults?'.format(self.MICRO_SERVICE)

    def send(self, method, *args, **kwargs):
        protocol = self.connection.get("protocol", None)
        host = self.connection.get("host", None)
        path = self.connection.get("path", None)
        assert protocol, "A protocol should be specified in the micro service configuration."
        assert host, "A host should be specified in the micro service configuration"
        assert path, "A path should be specified in the micro service configuration"
        args = (protocol, host, path) + args
        return super().send(method, *args, **kwargs)

    class Meta:
        abstract = True
