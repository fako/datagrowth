from __future__ import annotations

from typing import ClassVar, Type
from unittest.mock import Mock
from pathlib import Path

import pytest
import requests
from requests.models import Response
from requests.structures import CaseInsensitiveDict

from datagrowth.registry import Tag
from datagrowth.resources.http.extractors.requests import RequestsExtractor
from datagrowth.resources.http.pydantic import HttpResource, HttpInputsValidator
from datagrowth.signatures import DataMode, InputsValidator
from datagrowth.resources.storage.file_system import FileSystemStorage


class HttpResourceMockInputsValidator(HttpInputsValidator):
    POSITIONAL_NAMES: ClassVar[tuple[str, ...]] = ("method", "resource_type")

    resource_type: str
    slug: str
    page: str


class HttpResourceMock(HttpResource):

    NAMESPACE: ClassVar[Tag] = Tag(category="namespace", value="resource_http_mock")
    INPUTS_VALIDATOR: ClassVar[Type[InputsValidator]] = HttpResourceMockInputsValidator
    STORAGE: ClassVar[Tag | None] = Tag(category="storage", value="file_system")

    URI_TEMPLATE: ClassVar[str] = "https://example.com/{}/{slug}"
    PARAMETERS: ClassVar[dict[str, str] | None] = {
        "source": "tests",
        "page": "{page}",
    }
    HEADERS: ClassVar[dict[str, str]] = {
        "Accept": "application/json"
    }
    MODE: ClassVar[DataMode] = DataMode.JSON

    def auth_headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer super-secret-token"}

    def auth_parameters(self) -> dict[str, str]:
        return {"api_key": "super-secret-key"}


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


# ==============================
# extract
# ==============================


def configure_storage(resource: HttpResourceMock, root: Path, snapshots: bool = False,
                      allow_load: bool = True, allow_save: bool = True) -> None:
    assert isinstance(resource.storage, FileSystemStorage)
    resource.storage.config.update({
        "allow_read": True,
        "allow_write": True,
        "allow_save": allow_save,
        "allow_load": allow_load,
        "snapshots": snapshots,
        "directories": {
            "project": None,
            "data": str(root / "data"),
            "snapshots": str(root / "snapshots"),
            "tmp": str(root / "tmp"),
        },
    })


def test_extract_close_saves_resource_in_data_directory(resource: HttpResourceMock, mocked_session: Mock, tmp_path: Path) -> None:  # noqa: E501
    mocked_session.send.return_value = make_response(200, "{\"ok\": true}")
    configure_storage(resource, root=tmp_path, snapshots=False)

    extracted = resource.extract("get", "books", slug="python", page="1")
    extracted.close()

    assert extracted.signature is not None
    save_path = tmp_path / "data" / "httpresourcemock" / str(extracted.signature.hash) / "data.json"
    assert save_path.exists() is True
    assert save_path.read_text(encoding="utf-8") == extracted.model_dump_json(indent=4)
    assert (tmp_path / "snapshots" / "httpresourcemock" / str(extracted.signature.hash) / "data.json").exists() is False


def test_extract_close_saves_resource_in_snapshots_directory(resource: HttpResourceMock, mocked_session: Mock, tmp_path: Path) -> None:  # noqa: E501
    mocked_session.send.return_value = make_response(200, "{\"ok\": true}")
    configure_storage(resource, root=tmp_path, snapshots=True)
    assert isinstance(resource.storage, FileSystemStorage)

    extracted = resource.extract("get", "books", slug="python", page="1")
    extracted.close()

    assert extracted.signature is not None
    save_path = tmp_path / "snapshots" / "httpresourcemock" / str(extracted.signature.hash) / "data.json"
    assert save_path.exists() is True
    assert save_path.read_text(encoding="utf-8") == extracted.model_dump_json(indent=4)
    assert (tmp_path / "data" / "httpresourcemock" / str(extracted.signature.hash) / "data.json").exists() is False


def test_extract_close_skips_save_when_storage_disallows_it(resource: HttpResourceMock, mocked_session: Mock, tmp_path: Path) -> None:  # noqa: E501
    mocked_session.send.return_value = make_response(200, "{\"ok\": true}")
    configure_storage(resource, root=tmp_path, snapshots=False, allow_save=False)

    extracted = resource.extract("get", "books", slug="python", page="1")
    extracted.close()

    assert extracted.signature is not None
    data_path = tmp_path / "data" / str(extracted.signature.hash) / "data.json"
    snapshots_path = tmp_path / "snapshots" / str(extracted.signature.hash) / "data.json"
    assert data_path.exists() is False
    assert snapshots_path.exists() is False


def test_extract_uses_file_system_cache_before_extractor(resource: HttpResourceMock, mocked_session: Mock, tmp_path: Path) -> None:  # noqa: E501
    mocked_session.send.return_value = make_response(200, "{\"ok\": true}")
    configure_storage(resource, root=tmp_path, snapshots=False)

    extracted = resource.extract("get", "books", slug="python", page="1")
    extracted.close()

    mocked_session.send.reset_mock()
    cached = resource.extract("get", "books", slug="python", page="1")

    mocked_session.send.assert_not_called()
    assert extracted.signature is not None
    assert cached.signature is not None
    assert cached.signature.hash == extracted.signature.hash


def test_extract_allow_load_may_skip_file_system_cache(resource: HttpResourceMock, mocked_session: Mock, tmp_path: Path) -> None:  # noqa: E501
    mocked_session.send.side_effect = [
        make_response(200, "{\"ok\": true}"),
        make_response(200, "{\"ok\": false}"),
    ]
    configure_storage(resource, root=tmp_path, allow_load=False)

    extracted = resource.extract("get", "books", slug="python", page="1")
    extracted.close()

    refreshed = resource.extract("get", "books", slug="python", page="1")

    assert mocked_session.send.call_count == 2
    assert refreshed.result is not None
    assert refreshed.result.body == "{\"ok\": false}"


def test_storage_write_and_read_use_data_directory(resource: HttpResourceMock, mocked_session: Mock, tmp_path: Path) -> None:  # noqa: E501
    mocked_session.send.return_value = make_response(200, "{\"ok\": true}")
    configure_storage(resource, root=tmp_path, snapshots=False)
    assert isinstance(resource.storage, FileSystemStorage)

    extracted = resource.extract("get", "books", slug="python", page="1")
    assert extracted.signature is not None
    file_path = resource.storage.write(extracted.signature, "payload.txt", "hello world")

    assert file_path == tmp_path / "data" / "httpresourcemock" / str(extracted.signature.hash) / "payload.txt"
    assert file_path.exists() is True
    assert resource.storage.read(extracted.signature, "payload.txt") == "hello world"
    snapshot_path = (tmp_path / "snapshots" / "httpresourcemock" / str(extracted.signature.hash) / "payload.txt")
    assert snapshot_path.exists() is False


def test_storage_write_and_read_use_snapshots_directory(resource: HttpResourceMock, mocked_session: Mock, tmp_path: Path) -> None:  # noqa: E501
    mocked_session.send.return_value = make_response(200, "{\"ok\": true}")
    configure_storage(resource, root=tmp_path, snapshots=True)
    assert isinstance(resource.storage, FileSystemStorage)

    extracted = resource.extract("get", "books", slug="python", page="1")
    assert extracted.signature is not None
    file_path = resource.storage.write(extracted.signature, "blob.bin", b"\xff\xfe")

    assert file_path == tmp_path / "snapshots" / "httpresourcemock" / str(extracted.signature.hash) / "blob.bin"
    assert file_path.exists() is True
    assert resource.storage.read(extracted.signature, "blob.bin") == b"\xff\xfe"
    assert (tmp_path / "data" / "httpresourcemock" / str(extracted.signature.hash) / "blob.bin").exists() is False


def test_storage_write_and_read_use_tmp_directory(resource: HttpResourceMock, mocked_session: Mock, tmp_path: Path) -> None:  # noqa: E501
    mocked_session.send.return_value = make_response(200, "{\"ok\": true}")
    configure_storage(resource, root=tmp_path, snapshots=False)
    assert isinstance(resource.storage, FileSystemStorage)

    extracted = resource.extract("get", "books", slug="python", page="1")
    assert extracted.signature is not None
    file_path = resource.storage.write_tmp("tmp.bin", b"\xff\xfe")

    assert file_path == tmp_path / "tmp" / "tmp.bin"
    assert file_path.exists() is True
    assert resource.storage.read_tmp("tmp.bin") == b"\xff\xfe"
    assert (tmp_path / "data" / "httpresourcemock" / str(extracted.signature.hash) / "tmp.bin").exists() is False


def test_storage_write_rejects_absolute_filename(resource: HttpResourceMock, mocked_session: Mock, tmp_path: Path) -> None:  # noqa: E501
    mocked_session.send.return_value = make_response(200, "{\"ok\": true}")
    configure_storage(resource, root=tmp_path, snapshots=False)
    assert isinstance(resource.storage, FileSystemStorage)

    extracted = resource.extract("get", "books", slug="python", page="1")
    assert extracted.signature is not None
    with pytest.raises(ValueError, match="relative path"):
        resource.storage.write(extracted.signature, str(tmp_path / "absolute.txt"), "hello")


def test_storage_read_rejects_absolute_filename(resource: HttpResourceMock, mocked_session: Mock, tmp_path: Path) -> None:  # noqa: E501
    mocked_session.send.return_value = make_response(200, "{\"ok\": true}")
    configure_storage(resource, root=tmp_path, snapshots=False)
    assert isinstance(resource.storage, FileSystemStorage)

    extracted = resource.extract("get", "books", slug="python", page="1")
    assert extracted.signature is not None
    with pytest.raises(ValueError, match="relative path"):
        resource.storage.read(extracted.signature, str(tmp_path / "absolute.txt"))


def test_storage_write_rejects_nested_filename(resource: HttpResourceMock, mocked_session: Mock, tmp_path: Path) -> None:  # noqa: E501
    mocked_session.send.return_value = make_response(200, "{\"ok\": true}")
    configure_storage(resource, root=tmp_path, snapshots=False)
    assert isinstance(resource.storage, FileSystemStorage)

    extracted = resource.extract("get", "books", slug="python", page="1")
    assert extracted.signature is not None
    with pytest.raises(ValueError, match="Nested paths"):
        resource.storage.write(extracted.signature, "files/blob.bin", b"\xff\xfe")


def test_storage_read_rejects_nested_filename(resource: HttpResourceMock, mocked_session: Mock, tmp_path: Path) -> None:  # noqa: E501
    mocked_session.send.return_value = make_response(200, "{\"ok\": true}")
    configure_storage(resource, root=tmp_path, snapshots=False)
    assert isinstance(resource.storage, FileSystemStorage)

    extracted = resource.extract("get", "books", slug="python", page="1")
    assert extracted.signature is not None
    with pytest.raises(ValueError, match="Nested paths"):
        resource.storage.read(extracted.signature, "files/blob.bin")


def test_storage_write_rejects_reserved_data_json(resource: HttpResourceMock, mocked_session: Mock, tmp_path: Path) -> None:  # noqa: E501
    mocked_session.send.return_value = make_response(200, "{\"ok\": true}")
    configure_storage(resource, root=tmp_path, snapshots=False)
    assert isinstance(resource.storage, FileSystemStorage)

    extracted = resource.extract("get", "books", slug="python", page="1")
    assert extracted.signature is not None
    with pytest.raises(ValueError, match="reserved"):
        resource.storage.write(extracted.signature, "data.json", "{}")


def test_storage_read_rejects_reserved_data_json(resource: HttpResourceMock, mocked_session: Mock, tmp_path: Path) -> None:  # noqa: E501
    mocked_session.send.return_value = make_response(200, "{\"ok\": true}")
    configure_storage(resource, root=tmp_path, snapshots=False)
    assert isinstance(resource.storage, FileSystemStorage)

    extracted = resource.extract("get", "books", slug="python", page="1")
    extracted.close()
    assert extracted.signature is not None
    with pytest.raises(ValueError, match="reserved"):
        resource.storage.read(extracted.signature, "data.json")
