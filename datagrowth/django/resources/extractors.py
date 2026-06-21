from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.test import Client

from datagrowth.configuration import ConfigurationProperty, ConfigurationType
from datagrowth.registry import DATAGROWTH_REGISTRY, Tag
from datagrowth.resources.protocols import ResourceProtocol
from datagrowth.resources.pydantic import Result, Resource
from datagrowth.signatures import DataMode
from datagrowth.resources.http.signature import HttpSignature


class DjangoClientExtractor:

    tag = Tag(category="extractor", value="django_client")
    config = ConfigurationProperty(namespace="http_resource")

    def __init__(self, config: ConfigurationType) -> None:
        self.config = config
        self._client: Client = Client()

    def set_client(self, client: Client) -> None:
        self._client = client

    def _result_from_response(self, response) -> Result:
        # Get the headers from the response
        headers = {
            key: value[1]
            for key, value in response.headers._store.items()
        }
        # Capture cookies from the client's cookie jar (includes cookies set during redirects)
        if self._client.cookies:
            cookie_parts = [f"{key}={morsel.value}" for key, morsel in self._client.cookies.items()]
            if cookie_parts:
                headers["set-cookie"] = "; ".join(cookie_parts)
        # Create the Result
        content = response.content
        if content is None:
            body = None
        elif isinstance(content, str):
            body = content
        else:
            body = content.decode("utf-8", "replace")
        return Result(
            content_type=headers.get("content-type", "unknown/unknown"),
            head=headers,
            body=body,
        )

    def _apply_auth_cookies(self, signature: HttpSignature) -> None:
        """Parse cookies from auth headers and set them on the test client."""
        if not signature.auth or not signature.auth.headers:
            return
        cookie_header = signature.auth.headers.get("Cookie", "")
        if not cookie_header:
            return
        for cookie_pair in cookie_header.split(";"):
            cookie_pair = cookie_pair.strip()
            if "=" in cookie_pair:
                name, value = cookie_pair.split("=", 1)
                self._client.cookies[name.strip()] = value.strip()

    def _build_request_kwargs(self, signature: HttpSignature) -> dict:
        request_url = signature.url
        if signature.auth and signature.auth.parameters:
            split_url = urlsplit(request_url)
            params = dict(parse_qsl(split_url.query, keep_blank_values=True))
            params.update(signature.auth.parameters)
            request_url = urlunsplit((
                split_url.scheme,
                split_url.netloc,
                split_url.path,
                urlencode(params, doseq=True),
                split_url.fragment,
            ))

        request_kwargs: dict = {
            "path": request_url,
            "follow": self.config.allow_redirects,
        }

        headers = dict(signature.headers)
        if signature.auth and signature.auth.headers:
            for key, value in signature.auth.headers.items():
                if key.lower() != "cookie":
                    headers[key] = value
        if headers:
            request_kwargs["headers"] = headers

        if signature.method.lower() != "get":
            if signature.mode == DataMode.NONE:
                data = signature.get_data()
                if data:
                    request_kwargs["data"] = data
            elif signature.mode == DataMode.JSON:
                request_kwargs["data"] = signature.get_data()
                request_kwargs["content_type"] = "application/json; charset=utf-8"
            elif signature.mode == DataMode.DATA:
                request_kwargs["data"] = signature.get_data()
                request_kwargs["content_type"] = "application/octet-stream"
            elif signature.mode == DataMode.MULTIPART:
                raw_parts = signature.get_data()
                form_data: dict = {}
                for part in raw_parts:
                    if not isinstance(part, dict):
                        continue
                    if "content_type" in part and part["content_type"]:
                        filename = part.get("filename", part["name"])
                        form_data[part["name"]] = (filename, part["content"], part["content_type"])
                    else:
                        form_data[part["name"]] = part["content"]
                request_kwargs["data"] = form_data
            else:
                raise ValueError(f"Unsupported request mode: {signature.mode}")

        return request_kwargs

    @staticmethod
    def _error_resource(signature: HttpSignature, status: int, message: str) -> Resource[HttpSignature]:
        return Resource(
            signature=signature,
            status=status,
            result=Result(
                content_type="unknown/unknown",
                head={},
                body="",
                errors=message,
            ),
        )

    def extract(self, signature: HttpSignature) -> ResourceProtocol:
        self._apply_auth_cookies(signature)
        request_kwargs = self._build_request_kwargs(signature)
        method = signature.method.lower()

        try:
            client_method = getattr(self._client, method)
            response = client_method(**request_kwargs)
            resource = Resource(
                signature=signature,
                status=response.status_code,
                result=self._result_from_response(response),
            )
        except Exception as exc:
            resource = self._error_resource(signature, 500, str(exc))
        return resource


DATAGROWTH_REGISTRY.register_extractor(DjangoClientExtractor.tag, DjangoClientExtractor)
