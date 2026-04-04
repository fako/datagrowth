from typing import Any, ClassVar

from string import Formatter
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from pydantic import Field, field_validator

from datagrowth.exceptions import DGHttpError50X, DGHttpError40X
from datagrowth.registry import Tag
from datagrowth.signatures import InputsValidator
from datagrowth.resources.http.signature import HttpAuth, HttpSignature, HttpMode, HttpMethod
from datagrowth.resources.pydantic import Resource


class HttpResourceInputsValidator(InputsValidator):
    args: list[Any] = Field(min_length=1)

    @field_validator("args")
    @classmethod
    def validate_method(cls, args: list[Any]) -> list[Any]:
        HttpMethod(args[0])
        return args


class HttpResource(Resource[HttpSignature]):

    # Resource constants
    NAMESPACE: ClassVar[Tag] = Tag(category="namespace", value="http_resource")
    EXTRACTOR: ClassVar[Tag] = Tag(category="extractor", value="requests")

    # Http constants
    URI_TEMPLATE: ClassVar[str] = ""
    PARAMETERS: ClassVar[dict[str, str] | None] = {}
    DATA: ClassVar[dict[str, Any] | None] = {}
    HEADERS: ClassVar[dict[str, str]] = {}
    MODE: ClassVar[HttpMode] = HttpMode.NONE

    #####################
    # Http implementation
    #####################

    def headers(self, *args: Any, **kwargs: Any) -> dict[str, str]:
        """
        Returns the dictionary that should be used as headers for the request the resource will make.
        By default this is the dictionary from the ``HEADERS`` attribute.

        :param args: keyword arguments from the input (ignored by default)
        :param kwargs: keyword arguments from the input (ignored by default)
        :return: (dict) a dictionary representing HTTP headers
        """
        return dict(self.HEADERS)

    def parameters(self):
        """
        Returns the dictionary that should be added as HTTP query parameters for the request the resource will make.
        Add f-string syntax to the parameter keys or values to make them dynamic.

        :return: (dict) a dictionary representing HTTP query parameters
        """
        if self.PARAMETERS is None:  # some HttpResources like URLResource disallow dynamic PARAMETERS
            return {}
        return dict(self.PARAMETERS)

    def data(self, **kwargs: Any) -> dict[str, Any]:
        """
        Returns the dictionary that will be used as HTTP body for the request the resource will make.
        By default this is the dictionary from the ``DATA`` attribute
        updated with the kwargs from the input from the ``send`` method.

        :param kwargs: keyword arguments from the input
        :return:
        """
        if self.DATA is None:  # some HttpResources like most GET centered resources disallow dynamic DATA
            return {}
        data = dict(self.DATA)
        data.update(**kwargs)
        return data

    def _create_url(self, *args: Any, **kwargs: Any) -> tuple[str, dict[str, Any]]:
        """
        Build a URL from ``URI_TEMPLATE`` and return remaining kwargs not used in template substitution.

        These are the steps that this method makes:

        1) Start from ``URI_TEMPLATE`` and merge query parameters
           - Parse query params already present in ``URI_TEMPLATE``.
           - Merge in values from ``self.parameters()``.
           - Rebuild the template URL with the merged query string.

        2) Validate placeholders before formatting
           - Parse placeholders from the merged template URL.
           - Positional validation:
             * supports automatic placeholders: ``{}``
             * supports numbered placeholders: ``{0}``, ``{1}``, ...
             * rejects mixing automatic and numbered placeholders
             * enforces exact positional argument count
           - Named validation:
             * all named placeholders (e.g. ``{example}``) must be present in ``kwargs``
             * missing names raise ``KeyError``

        3) Format URL and compute unused kwargs
           - Format with ``str.format(*args, **template_kwargs)``.
           - Return kwargs not used in named placeholder substitution.

        Returns:
            tuple[str, dict[str, Any]]:
                - formatted URL
                - unused kwargs (safe to pass to body/data construction)
        """
        # Add parameters to the URI_TEMPLATE to allow dynamic replacement
        split_url = urlsplit(self.URI_TEMPLATE)
        params = dict[str, str](parse_qsl(split_url.query, keep_blank_values=True))
        parameters = self.parameters()
        params.update(parameters)
        query = urlencode(params, doseq=True, safe="{}")
        uri_template = urlunsplit((split_url.scheme, split_url.netloc, split_url.path, query, split_url.fragment))

        # Validate inputs and replace f-string placeholders in uri_template
        field_names = []
        for _, field_name, _, _ in Formatter().parse(uri_template):
            if field_name is not None:
                field_names.append(field_name)

        auto_positional_count = sum(1 for field_name in field_names if field_name == "")
        numbered_positions = sorted(
            int(field_name)
            for field_name in field_names
            if field_name.isdigit()
        )
        named_fields = {
            field_name
            for field_name in field_names
            if field_name and not field_name.isdigit()
        }

        if auto_positional_count and numbered_positions:
            raise ValueError("URI_TEMPLATE cannot mix automatic '{}' and numbered '{0}' positional placeholders.")

        if auto_positional_count:
            expected_args = auto_positional_count
            if len(args) != expected_args:
                raise ValueError(
                    f"URI_TEMPLATE expects exactly {expected_args} positional args, got {len(args)}."
                )
        elif numbered_positions:
            expected_args = numbered_positions[-1] + 1
            if len(args) != expected_args:
                raise ValueError(
                    f"URI_TEMPLATE expects exactly {expected_args} positional args, got {len(args)}."
                )
        elif args:
            raise ValueError(f"URI_TEMPLATE expects no positional args, got {len(args)}.")

        missing = sorted(name for name in named_fields if name not in kwargs)
        if missing:
            raise KeyError(f"Missing URI_TEMPLATE variables: {', '.join(missing)}")

        template_kwargs = {key: kwargs[key] for key in named_fields}
        formatted_url = uri_template.format(*args, **template_kwargs)
        unused_kwargs = {key: value for key, value in kwargs.items() if key not in named_fields}

        # Return the formatted URL and unused kwargs
        return formatted_url, unused_kwargs

    @staticmethod
    def uri_from_url(url: str) -> str:
        """
        Given a URL this method will strip the protocol and sort the parameters.
        That way a database lookup for a URL will always return URL's that logically match that URL.

        :param url: the URL to normalize to URI
        :return: a normalized URI suitable for lookups
        """
        split_url = urlsplit(url)
        params = sorted(parse_qsl(split_url.query, keep_blank_values=True), key=lambda item: item[0])
        normalized_url = urlunsplit((
            split_url.scheme,
            split_url.netloc,
            split_url.path,
            urlencode(params, doseq=True),
            split_url.fragment,
        ))
        if split_url.scheme:
            return normalized_url.replace(f"{split_url.scheme}://", "", 1)
        return normalized_url

    #####################
    # Auth
    #####################

    def auth_headers(self) -> dict[str, str]:
        """
        Returns the dictionary that should be used as authentication headers for the request the resource will make.
        Override this method in your own class to add authentication.
        By default this method returns an empty dictionary meaning there are no authentication headers.

        :return: (dict) dictionary with headers to add to requests
        """
        return {}

    def auth_parameters(self) -> dict[str, str]:
        """
        Returns the dictionary that should be used as authentication parameters for the request the resource will make.
        Override this method in your own class to add authentication.
        By default this method returns an empty dictionary meaning there are no authentication parameters.

        :return: (dict) dictionary with parameters to add to requests
        """
        return {}

    #####################
    # Resource protocol
    #####################

    def validate_inputs(self, *args: Any, **kwargs: Any) -> HttpResourceInputsValidator:
        return HttpResourceInputsValidator(args=args, kwargs=kwargs)

    def prepare_inputs(self, *args: Any, **kwargs: Any) -> HttpSignature:
        method = args[0]
        url_arguments = args[1:] if len(args) > 1 else []
        url, data_arguments = self._create_url(*url_arguments, **kwargs)
        auth = HttpAuth(headers=self.auth_headers(), parameters=self.auth_parameters())
        return HttpSignature(
            uri=self.uri_from_url(url),
            args=args,
            kwargs=kwargs,
            data=self.data(**data_arguments) if method != "get" or self.config.allow_get_body else None,
            method=method,
            url=url,
            headers=self.headers(*args, **kwargs),
            auth=auth if auth.headers or auth.parameters else None,
            mode=self.MODE,
        )

    @property
    def success(self) -> str:
        """
        Returns True if status is within HTTP success range

        :return: Boolean
        """
        return self.status is not None and 200 <= self.status < 209

    def handle_errors(self) -> None:
        """
        Raises exceptions upon error statuses
        Override this method to raise exceptions for your own error states.
        By default it raises the ``DGHttpError40X`` and ``DGHttpError50X`` exceptions for statuses.
        """
        class_name = self.__class__.__name__
        body = self.result.body if self.result and self.result.body is not None else ""
        if self.status >= 500:
            message = "{} > {} \n\n {}".format(class_name, self.status, body)
            raise DGHttpError50X(message, resource=self)
        elif self.status >= 400:
            message = "{} > {} \n\n {}".format(class_name, self.status, body)
            raise DGHttpError40X(message, resource=self)
        else:
            return None
