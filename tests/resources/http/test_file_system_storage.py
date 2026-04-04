from __future__ import annotations

from typing import ClassVar
from unittest.mock import Mock
from pathlib import Path

import pytest
import requests
from requests.models import Response
from requests.structures import CaseInsensitiveDict

from datagrowth.registry import Tag
from datagrowth.resources.http.extractors.requests import RequestsExtractor
from datagrowth.resources.http.pydantic import HttpResource
from datagrowth.resources.http.signature import HttpMode
from datagrowth.resources.storage.file_system import FileSystemStorage


class HttpResourceMock(HttpResource):

    NAMESPACE: ClassVar[Tag] = Tag(category="namespace", value="resource_http_mock")
    STORAGE: ClassVar[Tag] = Tag(category="storage", value="file_system")

    URI_TEMPLATE: ClassVar[str] = "https://example.com/{}/{slug}"
    PARAMETERS: ClassVar[dict[str, str]] = {
        "source": "tests",
        "page": "{page}",
    }
    HEADERS: ClassVar[dict[str, str]] = {
        "Accept": "application/json"
    }
    MODE: ClassVar[HttpMode] = HttpMode.JSON

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


def configure_storage(resource: HttpResourceMock, root: Path, snapshots: bool = False, allow_save: bool = True) -> None:
    assert isinstance(resource.storage, FileSystemStorage)
    resource.storage.config.update({
        "allow_read": True,
        "allow_write": True,
        "allow_save": allow_save,
        "allow_load": True,
        "force_save": False,
        "force_load": False,
        "snapshots": snapshots,
        "directories": {
            "tmp": str(root / "tmp"),
            "project": None,
            "data": str(root / "data"),
            "snapshots": str(root / "snapshots"),
        },
    })


def test_extract_close_saves_resource_in_data_directory(resource: HttpResourceMock, mocked_session: Mock, tmp_path: Path) -> None:  # noqa: E501
    mocked_session.send.return_value = make_response(200, "{\"ok\": true}")
    configure_storage(resource, root=tmp_path, snapshots=False)

    extracted = resource.extract("get", "books", slug="python", page="1")
    extracted.close()

    assert extracted.signature is not None
    save_path = tmp_path / "data" / "{}.json".format(extracted.signature.hash)
    assert save_path.exists() is True
    assert save_path.read_text(encoding="utf-8") == extracted.model_dump_json(indent=4)
    assert (tmp_path / "snapshots" / "{}.json".format(extracted.signature.hash)).exists() is False


def test_extract_close_saves_resource_in_snapshots_directory(resource: HttpResourceMock, mocked_session: Mock, tmp_path: Path) -> None:  # noqa: E501
    mocked_session.send.return_value = make_response(200, "{\"ok\": true}")
    configure_storage(resource, root=tmp_path, snapshots=True)
    assert isinstance(resource.storage, FileSystemStorage)

    extracted = resource.extract("get", "books", slug="python", page="1")
    extracted.close()

    assert extracted.signature is not None
    save_path = tmp_path / "snapshots" / "{}.json".format(extracted.signature.hash)
    assert save_path.exists() is True
    assert save_path.read_text(encoding="utf-8") == extracted.model_dump_json(indent=4)
    assert (tmp_path / "data" / "{}.json".format(extracted.signature.hash)).exists() is False


def test_extract_close_respects_storage_allow_save(resource: HttpResourceMock, mocked_session: Mock, tmp_path: Path) -> None:  # noqa: E501
    mocked_session.send.return_value = make_response(200, "{\"ok\": true}")
    configure_storage(resource, root=tmp_path, snapshots=False, allow_save=False)

    extracted = resource.extract("get", "books", slug="python", page="1")
    with pytest.raises(PermissionError, match="allow_save=false"):
        extracted.close()


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
