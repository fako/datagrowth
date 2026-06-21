import pytest

from datagrowth.resources.http.signature import HttpAuth, HttpMethod, HttpSignature
from datagrowth.signatures import DataBody, DataMode, DataPart


def test_http_signature_hash_includes_method() -> None:
    common = {
        "uri": "example.com/resource",
        "url": "http://example.com/resource",
        "data": {"a": 1},
        "mode": DataMode.JSON,
    }
    get_signature = HttpSignature(method=HttpMethod.GET, **common)
    post_signature = HttpSignature(method=HttpMethod.POST, **common)

    assert get_signature.hash != post_signature.hash


def test_http_signature_merges_auth_data_into_form_body_with_auth_winning() -> None:
    signature = HttpSignature(
        uri="example.com/login",
        url="https://example.com/login",
        method=HttpMethod.POST,
        data={"username": "admin", "password": None},
        auth=HttpAuth(data={"password": "adminpass"}),
        mode=DataMode.NONE,
    )

    assert signature.get_data() == {"username": "admin", "password": "adminpass"}


def test_http_signature_merges_auth_data_into_json_object() -> None:
    signature = HttpSignature(
        uri="example.com/login",
        url="https://example.com/login",
        method=HttpMethod.POST,
        data={"username": "admin"},
        auth=HttpAuth(data={"password": "adminpass"}),
        mode=DataMode.JSON,
    )

    assert signature.get_data() == '{"username":"admin","password":"adminpass"}'


def test_http_signature_returns_normal_data_without_auth_body() -> None:
    signature = HttpSignature(
        uri="example.com/login",
        url="https://example.com/login",
        method=HttpMethod.POST,
        data={"username": "admin"},
        auth=HttpAuth(headers={"Authorization": "Bearer token"}),
        mode=DataMode.JSON,
    )

    assert signature.get_data() == '{"username":"admin"}'


@pytest.mark.parametrize(
    ("mode", "data", "expected"),
    [
        (DataMode.JSON, ["public"], "JSON object body"),
        (DataMode.DATA, DataBody(content="cGF5bG9hZA=="), "dictionary body"),
        (DataMode.MULTIPART, [DataPart(name="public", content="value")], "dictionary body"),
    ],
)
def test_http_signature_rejects_auth_data_for_incompatible_bodies(mode, data, expected) -> None:
    signature = HttpSignature(
        uri="example.com/login",
        url="https://example.com/login",
        method=HttpMethod.POST,
        data=data,
        auth=HttpAuth(data={"password": "adminpass"}),
        mode=mode,
    )
    if mode in {DataMode.DATA, DataMode.MULTIPART}:
        signature.set_data_bytes(b"payload") if mode == DataMode.DATA else signature.set_data_parts([])

    with pytest.raises(TypeError, match=expected):
        signature.get_data()
