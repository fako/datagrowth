from __future__ import annotations

from datetime import datetime, timezone
from typing import ClassVar
from pathlib import Path
import pytest

from datagrowth.registry import Tag
from datagrowth.signatures import DataBody, DataMode
from datagrowth.resources.http.signature import HttpAuth
from datagrowth.vendors.apache.tika.resources import HttpTikaResource


class MockHttpTikaResource(HttpTikaResource):
    STORAGE: ClassVar[Tag | None] = Tag(category="storage", value="file_system")


class MockHttpTikaResourceAuth(MockHttpTikaResource):

    def auth_headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer micro-service-token"}

    def auth_parameters(self) -> dict[str, str]:
        return {"api_key": "micro-service-key"}


@pytest.fixture
def resource() -> MockHttpTikaResource:
    resource = MockHttpTikaResource()
    return resource


# ==============================
# validate_inputs
# ==============================


def test_validate_inputs_accepts_explicit_document_bytes(resource: MockHttpTikaResource) -> None:
    inputs = resource.validate_inputs("semantic", document=b"pdf-bytes")
    assert inputs.args == ("put", "semantic",)
    assert inputs.kwargs["mode"] == "semantic"
    assert inputs.kwargs["document"] == b"pdf-bytes"


def test_validate_inputs_rejects_multiple_sources(resource: MockHttpTikaResource) -> None:
    with pytest.raises(ValueError, match="Exactly one of 'document', 'file', or 'url' must be set"):
        resource.validate_inputs(document=b"pdf-bytes", url="https://example.com/input.pdf")


def test_validate_inputs_rejects_document_string(resource: MockHttpTikaResource) -> None:
    with pytest.raises(ValueError, match="document"):
        resource.validate_inputs(document="https://example.com/input.pdf")


# ==============================
# prepare_inputs
# ==============================


def test_prepare_inputs_uses_fetch_headers_for_url(resource: MockHttpTikaResource) -> None:
    signature = resource.prepare_inputs("put", mode="semantic", url="https://example.com/input.pdf")
    assert signature.mode == DataMode.DATA
    assert signature.data == DataBody(content="https://example.com/input.pdf")
    assert signature.headers["X-Tika-PDFextractMarkedContent"] == "true"
    assert signature.headers["fetcherName"] == "http"
    assert signature.headers["fetchKey"] == "https://example.com/input.pdf"


def test_prepare_inputs_sets_bytes_payload_for_document(resource: MockHttpTikaResource) -> None:
    signature = resource.prepare_inputs("put", mode="structure", document=b"pdf-bytes")
    assert signature.mode == DataMode.DATA
    assert isinstance(signature.data, DataBody)
    loc = signature.data.content
    assert isinstance(loc, str)
    assert loc.startswith("file://")
    tmp_path = Path(loc.removeprefix("file://"))
    assert resource.storage is not None
    expected_tmp = Path(*resource.storage.config.directories["tmp"])
    assert tmp_path.parent == Path(expected_tmp)
    assert tmp_path.read_bytes() == b"pdf-bytes"
    assert signature.kwargs["document"] == loc
    assert "fetcherName" not in signature.headers
    assert signature.headers["X-Tika-PDFextractMarkedContent"] == "false"


def test_prepare_inputs_reads_bytes_payload_from_file(resource: MockHttpTikaResource, tmp_path: Path) -> None:
    file_path = tmp_path / "document.pdf"
    file_path.write_bytes(b"file-bytes")
    signature = resource.prepare_inputs("put", mode="structure", file=file_path)
    assert signature.mode == DataMode.DATA
    assert signature.data == DataBody(content=f"file://{file_path}")
    assert signature.kwargs["file"] == str(file_path)


# ==============================
# prepare_inputs (auth)
# ==============================


def test_prepare_inputs_includes_auth_but_excludes_it_from_dump() -> None:
    resource = MockHttpTikaResourceAuth()
    signature = resource.prepare_inputs("put", mode="semantic", document=b"x")

    assert signature.auth == HttpAuth(
        headers={"Authorization": "Bearer micro-service-token"},
        parameters={"api_key": "micro-service-key"},
    )
    dumped_signature = signature.model_dump()
    assert "auth" not in dumped_signature
    assert "micro-service-token" not in str(dumped_signature)
    assert "micro-service-key" not in str(dumped_signature)


# ==============================
# extract
# ==============================


@pytest.mark.snapshots
def test_extract_file_input(resource: MockHttpTikaResource) -> None:
    pdf_path = Path(__file__).parent / "files" / "test.pdf"
    extracted = resource.extract(mode="semantic", file=pdf_path)
    extracted.close()

    if resource.storage is not None and resource.storage.config.snapshots:
        pytest.skip("Snapshots mode enabled: assertions disabled for snapshot recording.")

    assert extracted.signature is not None
    normalized_file = str(extracted.signature.kwargs["file"]).removeprefix("file://")
    assert isinstance(extracted.signature.data, DataBody)
    loc = extracted.signature.data.content
    normalized_data = str(loc).removeprefix("file://")
    assert normalized_file.endswith("vendors/apache/files/test.pdf")
    assert normalized_data.endswith("vendors/apache/files/test.pdf")
    assert extracted.result is not None
    assert extracted.result.created_at <= datetime.now(timezone.utc)
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
    assert extracted.result.created_at <= datetime.now(timezone.utc)
    assert extracted.status == 200


@pytest.mark.snapshots
def test_extract_url_input(resource: MockHttpTikaResource) -> None:
    extracted = resource.extract(mode="semantic", url="https://just-ask.data-scope.com/accounts/login/")
    extracted.close()

    if resource.storage is not None and resource.storage.config.snapshots:
        pytest.skip("Snapshots mode enabled: assertions disabled for snapshot recording.")

    assert extracted.signature is not None
    assert extracted.result is not None
    assert extracted.result.created_at <= datetime.now(timezone.utc)
    assert extracted.status == 200


@pytest.mark.snapshots
def test_extract_none_document_triggers_zero_byte_exception(resource: MockHttpTikaResource) -> None:
    extracted = resource.extract(mode="semantic", document=b"")
    extracted.close()

    if resource.storage is not None and resource.storage.config.snapshots:
        pytest.skip("Snapshots mode enabled: assertions disabled for snapshot recording.")

    assert extracted.signature is not None
    assert extracted.result is not None
    assert extracted.status == 1
    assert extracted.result.errors is not None
    assert "Tika returned exceptions without extracted content" in extracted.result.errors
    assert extracted.result.body is not None
    assert "ZeroByteFileException" in extracted.result.errors
