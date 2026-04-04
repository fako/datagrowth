from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

from datagrowth.configuration import ConfigurationType
from datagrowth.resources.http.extractors.requests import RequestsExtractor
from datagrowth.resources.http.signature import HttpMode
from datagrowth.vendors.apache.tika.resources import HttpTikaResource


@pytest.fixture
def mocked_session() -> Mock:
    session = Mock(spec=requests.Session)
    real_session = requests.Session()
    session.prepare_request.side_effect = real_session.prepare_request
    return session


@pytest.fixture
def config() -> ConfigurationType:
    config = ConfigurationType(namespace=["tika_resource", "micro_service", "http_resource", "global"])
    config.update({
        "connections": {
            "tika": {
                "protocol": "http",
                "host": "localhost:9998",
                "path": "/rmeta/text",
            },
        },
    })
    return config


@pytest.fixture
def resource(mocked_session: Mock, config: ConfigurationType) -> HttpTikaResource:
    resource = HttpTikaResource(config=config)
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


def test_validate_inputs_accepts_explicit_document_bytes(resource: HttpTikaResource) -> None:
    inputs = resource.validate_inputs("semantic", document=b"pdf-bytes")
    assert inputs.args == ["put", "semantic"]
    assert inputs.kwargs["mode"] == "semantic"
    assert inputs.kwargs["document"] == b"pdf-bytes"


def test_validate_inputs_rejects_multiple_sources(resource: HttpTikaResource) -> None:
    with pytest.raises(ValueError, match="Exactly one of 'document', 'file', or 'url' must be set"):
        resource.validate_inputs(document=b"pdf-bytes", url="https://example.com/input.pdf")


def test_validate_inputs_rejects_document_string(resource: HttpTikaResource) -> None:
    with pytest.raises(ValueError, match="document"):
        resource.validate_inputs(document="https://example.com/input.pdf")


def test_prepare_inputs_uses_fetch_headers_for_url(resource: HttpTikaResource) -> None:
    signature = resource.prepare_inputs("put", mode="semantic", url="https://example.com/input.pdf")
    assert signature.mode == HttpMode.BYTES
    assert signature.data is None
    assert signature.headers["X-Tika-PDFextractMarkedContent"] == "true"
    assert signature.headers["fetcherName"] == "http"
    assert signature.headers["fetchKey"] == "https://example.com/input.pdf"


def test_prepare_inputs_sets_bytes_payload_for_document(resource: HttpTikaResource) -> None:
    signature = resource.prepare_inputs("put", mode="structure", document=b"pdf-bytes")
    assert signature.mode == HttpMode.BYTES
    assert signature.data == b"pdf-bytes"
    assert "fetcherName" not in signature.headers
    assert signature.headers["X-Tika-PDFextractMarkedContent"] == "false"


def test_prepare_inputs_reads_bytes_payload_from_file(resource: HttpTikaResource, tmp_path: Path) -> None:
    file_path = tmp_path / "document.pdf"
    file_path.write_bytes(b"file-bytes")
    signature = resource.prepare_inputs("put", mode="structure", file=file_path)
    assert signature.mode == HttpMode.BYTES
    assert signature.data == b"file-bytes"
