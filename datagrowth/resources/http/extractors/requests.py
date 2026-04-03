from __future__ import annotations

from time import sleep
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests

from datagrowth.configuration import ConfigurationProperty, ConfigurationType
from datagrowth.registry import DATAGROWTH_REGISTRY, Tag
from datagrowth.resources.pydantic import Result
from datagrowth.resources.pydantic import Resource
from datagrowth.resources.http.signature import HttpMode, HttpSignature


class RequestsExtractor:

    tag = Tag(category="extractor", value="requests")
    config = ConfigurationProperty(namespace="http_resource")

    def __init__(self, config: ConfigurationType | dict[str, Any]) -> None:
        self.config = config
        self._session: requests.Session = requests.Session()

    def set_session(self, session: requests.Session) -> None:
        self._session = session

    @staticmethod
    def _result_from_response(response: requests.Response) -> Result:
        headers = {key.lower(): value for key, value in response.headers.items()}
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

    def _to_request(self, signature: HttpSignature) -> requests.Request:
        # Normalize headers
        headers = requests.utils.default_headers()
        headers["User-Agent"] = f"{self.config.user_agent}; {headers['User-Agent']}"
        # Remove encoding that Python 3.14 adds to the defaults, but isn't cross-version viable
        if "Accept-Encoding" in headers and headers["Accept-Encoding"].endswith("zstd"):
            headers["Accept-Encoding"] = headers["Accept-Encoding"].replace(", zstd", "")
        headers.update(signature.headers)
        if signature.auth and signature.auth.headers:
            headers.update(signature.auth.headers)
        # Add authentication to parameters
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
        # Make request based on library
        request_kwargs: dict[str, Any] = {
            "method": signature.method,
            "url": request_url,
            "headers": dict(headers),
        }
        if signature.method.lower() != "get" and signature.mode != HttpMode.NONE:
            if signature.mode == HttpMode.JSON:
                request_kwargs["json"] = signature.data
            elif signature.mode in {HttpMode.DATA, HttpMode.BYTES}:
                request_kwargs["data"] = signature.data
            elif signature.mode == HttpMode.MULTIPART:
                multipart_body = signature.data or {}
                request_kwargs["data"] = multipart_body.get("data")
                request_kwargs["files"] = multipart_body.get("files")
            else:
                raise ValueError(f"Unsupported request mode: {signature.mode}")
        return requests.Request(**request_kwargs)

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

    def extract(self, signature: HttpSignature) -> Resource[HttpSignature]:
        request = self._to_request(signature)
        prepared_request = self._session.prepare_request(request)

        for backoff_delay in [0] + list(self.config.backoff_delays):
            sleep(backoff_delay)
            try:
                response = self._session.send(
                    prepared_request,
                    proxies=self.config.requests_proxies,
                    verify=self.config.requests_verify,
                    timeout=self.config.timeout,
                    allow_redirects=self.config.allow_redirects,
                )
                resource = Resource(
                    signature=signature,
                    status=response.status_code,
                    result=self._result_from_response(response),
                )
            except requests.exceptions.SSLError:
                resource = self._error_resource(signature, 496, "SSL handshake/validation failed")
            except requests.Timeout:
                resource = self._error_resource(signature, 504, "Request timed out")
            except (requests.ConnectionError, IOError):
                resource = self._error_resource(signature, 502, "Connection failed")
            except UnicodeDecodeError:
                resource = self._error_resource(signature, 600, "Response decoding failed")
            if resource.status not in [420, 429, 502, 503, 504]:
                return resource
        return resource


DATAGROWTH_REGISTRY.register_extractor(RequestsExtractor.tag, RequestsExtractor)
