import pytest
from pydantic import ValidationError

from datagrowth.registry import Tag
from datagrowth.signatures import Signature
from datagrowth.resources.pydantic import Resource
from copy import deepcopy
from uuid import uuid4


@pytest.fixture
def resource_tag() -> Tag:
    return Tag(category="resource", value="x")


def test_signature_hash_no_data() -> None:
    s1 = Signature(uri="example://resource", data={})
    s2 = Signature(uri="example://resource")
    assert s1.hash == s2.hash

    s3 = Signature(uri="example://other", data={})
    assert s1.hash != s3.hash


def test_signature_hash_simple_data() -> None:
    d1 = {"a": 1, "b": 2}
    d2 = {"b": 2, "a": 1}  # different key order

    s1 = Signature(uri="example://resource", data=d1)
    s2 = Signature(uri="example://resource", data=d2)
    assert s1.hash == s2.hash

    d3 = {"a": 1, "b": 3}  # value change should affect hash
    s3 = Signature(uri="example://resource", data=d3)
    assert s1.hash != s3.hash


def test_signature_hash_nested_data() -> None:
    d1 = {"a": {"x": 1, "y": 2}, "b": 3}
    d2 = {"b": 3, "a": {"y": 2, "x": 1}}  # nested dict key order differs

    s1 = Signature(uri="example://resource", data=d1)
    s2 = Signature(uri="example://resource", data=d2)
    assert s1.hash == s2.hash

    # Dict inside list: dict key order differs but list order remains the same
    d3 = {"a": [{"y": 2, "x": 1}], "b": 3}
    d4 = {"a": [{"x": 1, "y": 2}], "b": 3}
    s3 = Signature(uri="example://resource", data=d3)
    s4 = Signature(uri="example://resource", data=d4)
    assert s3.hash == s4.hash


def test_signature_input_dict_not_mutated() -> None:
    original = {"a": {"x": 1, "y": 2}, "b": [{"k": 1}, {"k": 2}]}
    snapshot = deepcopy(original)
    _ = Signature(uri="example://resource", data=original)
    assert original == snapshot


def test_signature_respects_explicit_hash() -> None:
    explicit_hash = 123456789
    s1 = Signature(uri="example://resource", data={"a": 1}, hash=explicit_hash)
    assert s1.hash == explicit_hash


def test_signature_hash_bin_payload() -> None:
    s1 = Signature(uri="example://resource", data={"payload": "bin://hello-world"})
    s2 = Signature(uri="example://resource", data={"payload": "bin://hello-world"})
    s3 = Signature(uri="example://resource", data={"payload": "bin://goodbye-world"})
    assert s1.hash == s2.hash
    assert s1.hash != s3.hash


def test_signature_get_data_requires_open_for_bin_data() -> None:
    signature = Signature(uri="example://resource", data={"payload": "bin://cGRmLWJ5dGVz"})
    with pytest.raises(RuntimeError, match="requires a signature to be open"):
        signature.get_data()


def test_signature_set_data_and_close_lifecycle_for_bin_data() -> None:
    signature = Signature(uri="example://resource", data={"payload": "bin://cGRmLWJ5dGVz"})

    signature.set_data_bytes(b"pdf-bytes")
    assert signature.get_data() == b"pdf-bytes"

    signature.close()
    with pytest.raises(RuntimeError, match="requires a signature to be open"):
        signature.get_data()


def test_signature_type_allows_filesystem_safe_values() -> None:
    signature = Signature(uri="example://resource", type="prompt-v1.json")
    assert signature.type == "prompt-v1.json"


@pytest.mark.parametrize("signature_type", ["", ".", "..", "folder/name", "folder\\name", "name with spaces"])
def test_signature_type_rejects_filesystem_unsafe_values(signature_type: str) -> None:
    with pytest.raises(ValidationError):
        Signature(uri="example://resource", type=signature_type)


def test_resource_eq_with_non_resource_returns_false(resource_tag: Tag) -> None:
    s1 = Signature(uri="example://resource", data={"a": 1})
    r1 = Resource(type=resource_tag, signature=s1)
    assert (r1 == object()) is False


def test_resource_equality_by_signature(resource_tag: Tag) -> None:
    s1 = Signature(uri="example://resource", data={"a": 1, "b": [1, 2]})
    s2 = Signature(uri="example://resource", data={"b": [1, 2], "a": 1})
    r1 = Resource(type=resource_tag, signature=s1)
    r2 = Resource(type=resource_tag, signature=s2)
    assert r1 == r2
    assert hash(r1) == hash(r2)
    assert len({r1, r2}) == 1


def test_resource_inequality_by_signature_difference(resource_tag: Tag) -> None:
    s1 = Signature(uri="example://resource", data={"a": 1})
    s2 = Signature(uri="example://resource", data={"a": 2})
    r1 = Resource(type=resource_tag, signature=s1)
    r2 = Resource(type=resource_tag, signature=s2)
    assert r1 != r2


def test_resource_mixed_signature_and_no_signature_not_equal(resource_tag: Tag) -> None:
    shared_id = uuid4()
    s = Signature(uri="example://resource", data={"a": 1})
    r_sig = Resource(type=resource_tag, signature=s, id=shared_id)
    r_no_sig = Resource(type=resource_tag, id=shared_id)
    assert r_sig != r_no_sig


def test_resource_equality_by_id_when_no_signatures(resource_tag: Tag) -> None:
    shared_id = uuid4()
    r1 = Resource(type=resource_tag, id=shared_id)
    r2 = Resource(type=resource_tag, id=shared_id)
    assert r1 == r2
    assert hash(r1) == hash(r2)
    assert len({r1, r2}) == 1


def test_resource_inequality_by_id_when_no_signatures(resource_tag: Tag) -> None:
    r1 = Resource(type=resource_tag)
    r2 = Resource(type=resource_tag)
    assert r1 != r2
