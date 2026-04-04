from __future__ import annotations

from typing import ClassVar
from unittest.mock import Mock

import pytest
import requests
from pydantic import ValidationError
from requests.models import Response
from requests.structures import CaseInsensitiveDict

from datagrowth.registry import Tag
from datagrowth.resources.http.extractors.requests import RequestsExtractor
from datagrowth.resources.http.pydantic import URLResource
from datagrowth.resources.http.signature import HttpMethod, HttpSignature


class URLResourceMock(URLResource):
    NAMESPACE: ClassVar[Tag] = Tag(category="namespace", value="resource_url_mock")


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
def resource(mocked_session: Mock) -> URLResourceMock:
    resource = URLResourceMock()
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


# ==============================
# validate_inputs
# ==============================


def test_validate_inputs_accepts_valid_url(resource: URLResourceMock) -> None:
    inputs = resource.validate_inputs("https://example.com/api")
    assert len(inputs.args) == 1
    assert inputs.kwargs == {}


def test_validate_inputs_rejects_bare_string(resource: URLResourceMock) -> None:
    with pytest.raises(ValidationError):
        resource.validate_inputs("not-a-url")


def test_validate_inputs_rejects_empty_call(resource: URLResourceMock) -> None:
    with pytest.raises(ValidationError):
        resource.validate_inputs()


def test_validate_inputs_rejects_kwargs(resource: URLResourceMock) -> None:
    with pytest.raises(ValidationError):
        resource.validate_inputs("https://example.com", extra="bad")


def test_validate_inputs_rejects_multiple_args(resource: URLResourceMock) -> None:
    with pytest.raises(ValidationError):
        resource.validate_inputs("https://a.com", "https://b.com")


# ==============================
# extract
# ==============================


def test_extract_sends_get_request(resource: URLResourceMock, mocked_session: Mock) -> None:
    mocked_session.send.return_value = make_response(200, '{"ok": true}')

    extracted = resource.extract("https://example.com/data")

    assert isinstance(extracted, URLResourceMock)
    assert extracted.status == 200
    assert extracted.success is True
    assert extracted.result is not None
    assert extracted.result.content_type == "application/json"
    assert extracted.result.body == '{"ok": true}'
    assert extracted.signature is not None
    assert isinstance(extracted.signature, HttpSignature)
    assert extracted.signature.method == HttpMethod.GET
    assert extracted.signature.url == "https://example.com/data"
    assert extracted.signature.uri == "example.com/data"
    mocked_session.send.assert_called_once()
    prepared_request = mocked_session.send.call_args.args[0]
    assert prepared_request.method == "GET"
    assert prepared_request.url == "https://example.com/data"


def test_extract_preserves_query_parameters(resource: URLResourceMock, mocked_session: Mock) -> None:
    mocked_session.send.return_value = make_response(200, '{"results": []}')

    extracted = resource.extract("https://example.com/search?q=test&page=2")

    assert extracted.status == 200
    assert extracted.signature is not None
    assert extracted.signature.url == "https://example.com/search?q=test&page=2"
    prepared_request = mocked_session.send.call_args.args[0]
    assert prepared_request.url == "https://example.com/search?q=test&page=2"


def test_extract_rejects_non_url(resource: URLResourceMock) -> None:
    with pytest.raises(ValidationError):
        resource.extract("not-a-url")


def test_extract_rejects_extra_kwargs(resource: URLResourceMock) -> None:
    with pytest.raises(ValidationError):
        resource.extract("https://example.com", query="nope")
