import pytest
from pydantic import BaseModel

from datagrowth.utils.classes import serialize_class_reference, deserialize_class_reference


class PlainClass:
    pass


class ModelClass(BaseModel):
    value: str


def test_serialize_class_reference_without_prefix() -> None:
    serialized = serialize_class_reference(PlainClass)
    assert serialized == f"{PlainClass.__module__}.{PlainClass.__qualname__}"


def test_deserialize_class_reference_without_prefix() -> None:
    path = f"{PlainClass.__module__}.{PlainClass.__qualname__}"
    deserialized = deserialize_class_reference(path)
    assert deserialized is PlainClass


def test_serialize_class_reference_with_prefix_only_marks_basemodel_classes() -> None:
    serialized_model = serialize_class_reference(ModelClass, prefix="basemodel")
    serialized_plain = serialize_class_reference(PlainClass, prefix="basemodel")
    assert serialized_model == f"basemodel:{ModelClass.__module__}.{ModelClass.__qualname__}"
    assert serialized_plain == f"{PlainClass.__module__}.{PlainClass.__qualname__}"


def test_deserialize_class_reference_with_prefix_skips_non_prefixed_strings() -> None:
    prefixed_path = f"basemodel:{ModelClass.__module__}.{ModelClass.__qualname__}"
    plain_path = f"{PlainClass.__module__}.{PlainClass.__qualname__}"
    assert deserialize_class_reference(prefixed_path, prefix="basemodel") is ModelClass
    assert deserialize_class_reference(plain_path, prefix="basemodel") == plain_path


def test_class_reference_serialization_and_deserialization_supports_nested_containers() -> None:
    payload = (
        {"output": ModelClass, "plain": PlainClass},
        [ModelClass, {"nested": ModelClass}],
    )

    serialized = serialize_class_reference(payload, prefix="basemodel")
    assert serialized == (
        {
            "output": f"basemodel:{ModelClass.__module__}.{ModelClass.__qualname__}",
            "plain": f"{PlainClass.__module__}.{PlainClass.__qualname__}",
        },
        [
            f"basemodel:{ModelClass.__module__}.{ModelClass.__qualname__}",
            {"nested": f"basemodel:{ModelClass.__module__}.{ModelClass.__qualname__}"},
        ],
    )

    deserialized = deserialize_class_reference(serialized, prefix="basemodel")
    assert deserialized[0]["output"] is ModelClass
    assert deserialized[0]["plain"] == f"{PlainClass.__module__}.{PlainClass.__qualname__}"
    assert deserialized[1][0] is ModelClass
    assert deserialized[1][1]["nested"] is ModelClass


def test_deserialize_class_reference_reports_invalid_import_path() -> None:
    faulty_path = "not_a_real_module.or_class"
    with pytest.raises(ImportError, match=f"Could not import class path '{faulty_path}'"):
        deserialize_class_reference(faulty_path)


def test_deserialize_class_reference_reports_type_mismatch() -> None:
    with pytest.raises(TypeError, match="Expected class import from path"):
        deserialize_class_reference("datagrowth.registry.types._get_config_namespace")
