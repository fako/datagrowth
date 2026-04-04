from __future__ import annotations

from datetime import datetime
from typing import ClassVar
from pathlib import Path
import pytest

from datagrowth.registry import Tag
from datagrowth.resources.http.signature import HttpMode
from datagrowth.vendors.apache.tika.resources import HttpTikaResource


class MockHttpTikaResource(HttpTikaResource):
    STORAGE: ClassVar[Tag] = Tag(category="storage", value="file_system")


@pytest.fixture
def resource() -> MockHttpTikaResource:
    resource = MockHttpTikaResource()
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
    assert signature.data == b"https://example.com/input.pdf"
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


@pytest.mark.snapshots
def test_extract_file_input(resource: MockHttpTikaResource) -> None:
    pdf_path = Path(__file__).parent / "files" / "test.pdf"
    extracted = resource.extract(mode="semantic", file=pdf_path)
    extracted.close()

    if resource.storage is not None and resource.storage.config.snapshots:
        pytest.skip("Snapshots mode enabled: assertions disabled for snapshot recording.")

    assert extracted.signature is not None
    assert extracted.result is not None
    assert extracted.result.created_at <= datetime.now()
    assert extracted.status == 200


@pytest.mark.snapshots
def test_extract_document_input(resource: MockHttpTikaResource) -> None:
    pdf_path = Path(__file__).parent / "files" / "test.pdf"
    extracted = resource.extract(mode="structure", document=pdf_path.read_bytes())
    extracted.close()

    if resource.storage is not None and resource.storage.config.snapshots:
        pytest.skip("Snapshots mode enabled: assertions disabled for snapshot recording.")

    assert extracted.signature is not None
    assert extracted.result is not None
    assert extracted.result.created_at <= datetime.now()
    assert extracted.status == 200


@pytest.mark.snapshots
def test_extract_url_input(resource: MockHttpTikaResource) -> None:
    extracted = resource.extract(mode="semantic", url="https://just-ask.data-scope.com/accounts/login/")
    extracted.close()

    if resource.storage is not None and resource.storage.config.snapshots:
        pytest.skip("Snapshots mode enabled: assertions disabled for snapshot recording.")

    assert extracted.signature is not None
    assert extracted.result is not None
    assert extracted.result.created_at <= datetime.now()
    assert extracted.status == 200
