from datagrowth.resources.http.signature import HttpMethod, HttpSignature
from datagrowth.signatures import DataMode


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
