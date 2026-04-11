from __future__ import annotations

import json
import base64
from typing import ClassVar
from unittest.mock import Mock
from pathlib import Path

import pytest
import requests
from requests.models import Response
from requests.structures import CaseInsensitiveDict

from pydantic import ValidationError

from datagrowth.registry import Tag
from datagrowth.exceptions import DGHttpError40X, DGHttpError50X
from datagrowth.resources.http.extractors.requests import RequestsExtractor
from datagrowth.resources.http.pydantic import HttpResource
from datagrowth.resources.http.signature import HttpAuth, HttpMode, HttpSignature
from datagrowth.resources.pydantic import Result


class HttpResourceMock(HttpResource):

    NAMESPACE: ClassVar[Tag] = Tag(category="namespace", value="resource_http_mock")
    URI_TEMPLATE: ClassVar[str] = "https://example.com/{}/{slug}"
    PARAMETERS: ClassVar[dict[str, str]] = {
        "source": "tests",
        "page": "{page}",
    }
    HEADERS: ClassVar[dict[str, str]] = {
        "Accept": "application/json"
    }
    MODE: ClassVar[HttpMode] = HttpMode.JSON


class HttpResourceAuthMock(HttpResourceMock):

    NAMESPACE: ClassVar[Tag] = Tag(category="namespace", value="resource_http_auth_mock")

    def auth_headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer super-secret-token"}

    def auth_parameters(self) -> dict[str, str]:
        return {"api_key": "super-secret-key"}


class HttpResourceDataMock(HttpResource):

    NAMESPACE: ClassVar[Tag] = Tag(category="namespace", value="resource_http_data_mock")
    STORAGE: ClassVar[Tag] = Tag(category="storage", value="file_system")
    URI_TEMPLATE: ClassVar[str] = "https://example.com/upload"
    MODE: ClassVar[HttpMode] = HttpMode.DATA

    def data(self, **kwargs: str) -> str:
        return f"bin://file://{kwargs['file']}"


class HttpResourceDataNoStorageMock(HttpResource):

    NAMESPACE: ClassVar[Tag] = Tag(category="namespace", value="resource_http_data_no_storage_mock")
    URI_TEMPLATE: ClassVar[str] = "https://example.com/upload"
    MODE: ClassVar[HttpMode] = HttpMode.DATA

    def data(self, **kwargs: str) -> str:
        return f"bin://{base64.b64encode(b'payload-bytes').decode('ascii')}"


def make_response(status_code: int, body: bytes | str, headers: dict[str, str] | None = None) -> Response:
    response = Response()
    response.status_code = status_code
    response.headers = CaseInsensitiveDict(headers or {"content-type": "application/json"})
    response._content = body.encode("utf-8") if isinstance(body, str) else body  # noqa: SLF001
    return response


@pytest.fixture
def mocked_session() -> Mock:
    session = Mock(spec=requests.Session)
    real_session = requests.Session()
    session.prepare_request.side_effect = real_session.prepare_request
    return session


@pytest.fixture
def resource(mocked_session: Mock) -> HttpResourceMock:
    resource = HttpResourceMock()
    assert isinstance(resource.extractor, RequestsExtractor)
    resource.extractor.set_session(mocked_session)
    resource.extractor.config.update({
        "backoff_delays": [],
        "requests_proxies": None,
        "requests_verify": True,
        "allow_redirects": True,
        "timeout": 30,
        "user_agent": "DataGrowth (test)",
    })
    return resource


@pytest.fixture
def data_resource(mocked_session: Mock, tmp_path: Path) -> HttpResourceDataMock:
    resource = HttpResourceDataMock()
    assert isinstance(resource.extractor, RequestsExtractor)
    resource.extractor.set_session(mocked_session)
    resource.extractor.config.update({
        "backoff_delays": [],
        "requests_proxies": None,
        "requests_verify": True,
        "allow_redirects": True,
        "timeout": 30,
        "user_agent": "DataGrowth (test)",
    })
    assert resource.storage is not None
    resource.storage.config.update({
        "allow_read": True,
        "allow_write": True,
        "allow_save": False,
        "allow_load": False,
        "snapshots": False,
        "directories": {
            "project": None,
            "data": str(tmp_path / "data"),
            "snapshots": str(tmp_path / "snapshots"),
            "tmp": str(tmp_path / "tmp"),
        },
    })
    return resource


# ==============================
# validate_inputs
# ==============================

def test_validate_inputs_accepts_supported_http_methods(resource: HttpResourceMock) -> None:
    for method in ("get", "post", "put", "head", "patch"):
        inputs = resource.validate_inputs(method, "books", slug="python", page="1")
        assert inputs.args[0] == method


def test_validate_inputs_rejects_unsupported_method(resource: HttpResourceMock) -> None:
    with pytest.raises(ValidationError, match="args"):
        resource.validate_inputs("delete", "books", slug="python", page="1")


def test_validate_inputs_rejects_empty_call(resource: HttpResourceMock) -> None:
    with pytest.raises(ValidationError, match="too_short"):
        resource.validate_inputs()


# ==============================
# prepare_inputs
# ==============================

def test_prepare_inputs_creates_http_signature_with_template_data(resource: HttpResourceMock) -> None:
    signature = resource.prepare_inputs("get", "books", slug="python", page="2")

    assert isinstance(signature, HttpSignature)
    assert signature.url == "https://example.com/books/python?source=tests&page=2"
    assert signature.uri == "example.com/books/python?page=2&source=tests"
    assert signature.mode == HttpMode.JSON
    assert signature.data is None
    assert signature.headers == {"Accept": "application/json"}


def test_prepare_inputs_rejects_invalid_url_placeholders(resource: HttpResourceMock) -> None:
    with pytest.raises(ValueError, match="expects exactly 1 positional args"):
        resource.prepare_inputs("get")

    with pytest.raises(KeyError, match="Missing URI_TEMPLATE variables: page, slug"):
        resource.prepare_inputs("get", "books")


def test_prepare_inputs_includes_auth_but_excludes_it_from_dump(mocked_session: Mock) -> None:
    resource = HttpResourceAuthMock()
    assert isinstance(resource.extractor, RequestsExtractor)
    resource.extractor.set_session(mocked_session)
    signature = resource.prepare_inputs("get", "books", slug="python", page="2")

    assert signature.auth == HttpAuth(
        headers={"Authorization": "Bearer super-secret-token"},
        parameters={"api_key": "super-secret-key"},
    )
    dumped_signature = signature.model_dump()
    assert "auth" not in dumped_signature
    assert "super-secret-token" not in str(dumped_signature)
    assert "super-secret-key" not in str(dumped_signature)


# ==============================
# extract
# ==============================

def test_resource_extract_get_uses_requests_extractor(resource: HttpResourceMock, mocked_session: Mock) -> None:
    mocked_session.send.return_value = make_response(200, "{\"ok\": true}")

    extracted_resource = resource.extract("get", "books", slug="python", page="1")

    assert isinstance(extracted_resource, HttpResourceMock)
    assert extracted_resource.status == 200
    assert extracted_resource.success is True
    assert extracted_resource.result is not None
    assert extracted_resource.result.content_type == "application/json"
    assert extracted_resource.result.body == "{\"ok\": true}"
    content_type, data = extracted_resource.content
    assert content_type == "application/json"
    assert data == {"ok": True}
    assert extracted_resource.signature is not None
    assert extracted_resource.signature.url == "https://example.com/books/python?source=tests&page=1"
    mocked_session.send.assert_called_once()
    prepared_request = mocked_session.send.call_args.args[0]
    assert prepared_request.method == "GET"
    assert prepared_request.url == "https://example.com/books/python?source=tests&page=1"


def test_resource_extract_applies_auth_to_request_not_signature_dump(mocked_session: Mock) -> None:
    mocked_session.send.return_value = make_response(200, "{\"ok\": true}")
    resource = HttpResourceAuthMock()
    assert isinstance(resource.extractor, RequestsExtractor)
    resource.extractor.set_session(mocked_session)
    resource.extractor.config.update({
        "backoff_delays": [],
        "requests_proxies": None,
        "requests_verify": True,
        "allow_redirects": True,
        "timeout": 30,
        "user_agent": "DataGrowth (test)",
    })

    extracted_resource = resource.extract("get", "books", slug="python", page="1")

    assert extracted_resource.signature is not None
    dumped_signature = extracted_resource.signature.model_dump()
    assert "auth" not in dumped_signature
    prepared_request = mocked_session.send.call_args.args[0]
    assert prepared_request.headers["Authorization"] == "Bearer super-secret-token"
    assert prepared_request.url == "https://example.com/books/python?source=tests&page=1&api_key=super-secret-key"


def test_resource_extract_post_sends_json_data(resource: HttpResourceMock, mocked_session: Mock) -> None:
    mocked_session.send.return_value = make_response(200, "{\"ok\": true}")

    _ = resource.extract("post", "books", slug="python", page="1", query="django")

    mocked_session.send.assert_called_once()
    prepared_request = mocked_session.send.call_args.args[0]
    assert prepared_request.method == "POST"
    assert prepared_request.url == "https://example.com/books/python?source=tests&page=1"
    assert json.loads(prepared_request.body.decode("utf-8")) == {"query": "django"}


def test_resource_extract_data_mode_requires_open_signature(mocked_session: Mock) -> None:
    mocked_session.send.return_value = make_response(200, "{\"ok\": true}")
    resource = HttpResourceDataNoStorageMock()
    assert isinstance(resource.extractor, RequestsExtractor)
    resource.extractor.set_session(mocked_session)
    resource.extractor.config.update({
        "backoff_delays": [],
        "requests_proxies": None,
        "requests_verify": True,
        "allow_redirects": True,
        "timeout": 30,
        "user_agent": "DataGrowth (test)",
    })
    with pytest.raises(RuntimeError, match="requires a signature to be open"):
        resource.extract("post")


def test_resource_extract_data_mode_uses_hydrated_signature_data(data_resource: HttpResourceDataMock,
                                                                 mocked_session: Mock, tmp_path: Path) -> None:
    mocked_session.send.return_value = make_response(200, "{\"ok\": true}")
    payload_path = tmp_path / "payload.bin"
    payload_path.write_bytes(b"payload-bytes")

    _ = data_resource.extract("post", file=str(payload_path))
    prepared_request = mocked_session.send.call_args.args[0]
    assert prepared_request.body == b"payload-bytes"


def test_resource_extract_retries_on_retryable_status(resource: HttpResourceMock, mocked_session: Mock) -> None:
    assert isinstance(resource.extractor, RequestsExtractor)
    resource.extractor.config.update({"backoff_delays": [0]})
    mocked_session.send.side_effect = [
        make_response(502, "{\"error\": true}"),
        make_response(200, "{\"ok\": true}"),
    ]

    extracted_resource = resource.extract("get", "books", slug="python", page="1")

    assert extracted_resource.status == 200
    assert mocked_session.send.call_count == 2

# ==============================
# results, success, errors
# ==============================


def test_resource_success_property_depends_on_http_status(resource: HttpResourceMock) -> None:
    resource.status = 200
    resource.result = None
    assert resource.success is True
    resource.status = 208
    assert resource.success is True
    resource.status = 404
    assert resource.success is False


def test_resource_content_parses_body_on_non_success(resource: HttpResourceMock) -> None:
    resource.status = 404
    resource.result = Result(
        content_type="application/json",
        body="{\"ok\": false}",
        errors="{\"error\": \"not found\"}",
    )

    content_type, data = resource.content
    assert content_type == "application/json"
    assert data == {"ok": False}


def test_resource_handle_errors_raises_40x(resource: HttpResourceMock) -> None:
    resource.status = 404
    resource.result = Result(content_type="application/json", body="missing", errors=None)

    with pytest.raises(DGHttpError40X, match="HttpResourceMock > 404"):
        resource.handle_errors()


def test_resource_handle_errors_raises_50x(resource: HttpResourceMock) -> None:
    resource.status = 500
    resource.result = Result(content_type="application/json", body="server exploded", errors=None)

    with pytest.raises(DGHttpError50X, match="HttpResourceMock > 500"):
        resource.handle_errors()


def test_resource_handle_errors_returns_true_for_success(resource: HttpResourceMock) -> None:
    resource.status = 200
    resource.result = Result(content_type="application/json", body="{\"ok\": true}", errors=None)

    assert resource.handle_errors() is None
