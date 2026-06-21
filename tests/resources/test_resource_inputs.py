import pytest
from pydantic import ValidationError
from typing import Literal

from datagrowth.signatures import InputsSecurityLevel, InputsValidator


class ExampleInputsValidator(InputsValidator):
    POSITIONAL_NAMES = ("method", "resource_id")

    method: Literal["get", "post"] = "get"
    resource_id: int
    page: int = 1


class SecureInputsValidator(InputsValidator):
    SENSITIVE_NAMES = ("password",)

    username: str
    password: str


def test_inputs_validator_from_inputs_prefers_kwargs_over_args() -> None:
    validator = ExampleInputsValidator.from_inputs("get", 7, method="post", page=3)

    assert validator.method == "post"
    assert validator.resource_id == 7
    assert validator.page == 3
    assert validator.args == ("post", 7)
    assert validator.kwargs == {"page": 3, "method": "post"}
    assert validator.get_argument("method") == "post"
    assert validator.get_argument("resource_id") == 7
    assert validator.get_argument("page") == 3
    assert validator.get_argument("does_not_exist") is None


def test_inputs_validator_from_inputs_ignores_unspecified_inputs() -> None:
    validator = ExampleInputsValidator.from_inputs("post", 7, "ignored", page=2, ignored=True)

    assert validator.method == "post"
    assert validator.resource_id == 7
    assert validator.page == 2
    assert "ignored" not in validator.model_dump()
    assert "ignored" not in validator.args
    assert validator.get_argument("ignored") is None


def test_inputs_validator_from_inputs_applies_subclass_field_validation() -> None:
    with pytest.raises(ValidationError):
        ExampleInputsValidator.from_inputs("delete", 3)


def test_inputs_validator_from_inputs_uses_validated_values_for_args_and_kwargs() -> None:
    validator = ExampleInputsValidator.from_inputs("post", "8", page="4")

    assert validator.args == ("post", 8)
    assert validator.kwargs == {"page": 4}


def test_inputs_validator_dump_is_secure_by_default() -> None:
    validator = SecureInputsValidator.from_inputs(username="admin", password="adminpass")

    assert validator.model_dump() == {
        "args": (),
        "kwargs": {"username": "admin"},
        "username": "admin",
    }
    assert "adminpass" not in validator.model_dump_json()


def test_inputs_validator_can_dump_only_sensitive_inputs() -> None:
    validator = SecureInputsValidator.from_inputs(username="admin", password="adminpass")

    assert validator.model_dump(context={"security_level": InputsSecurityLevel.SENSITIVE}) == {
        "args": (),
        "kwargs": {"password": "adminpass"},
        "password": "adminpass",
    }


def test_inputs_validator_can_dump_insecure_inputs() -> None:
    validator = SecureInputsValidator.from_inputs(username="admin", password="adminpass")

    assert validator.model_dump(context={"security_level": InputsSecurityLevel.INSECURE}) == {
        "args": (),
        "kwargs": {"username": "admin", "password": "adminpass"},
        "username": "admin",
        "password": "adminpass",
    }


def test_inputs_validator_rejects_unknown_sensitive_names() -> None:
    with pytest.raises(TypeError, match="unknown input fields: token"):
        class UnknownSensitiveInputsValidator(InputsValidator):
            SENSITIVE_NAMES = ("token",)


def test_inputs_validator_rejects_sensitive_positional_names() -> None:
    with pytest.raises(TypeError, match="Sensitive input fields cannot be positional: password"):
        class PositionalSensitiveInputsValidator(InputsValidator):
            POSITIONAL_NAMES = ("password",)
            SENSITIVE_NAMES = ("password",)

            password: str
