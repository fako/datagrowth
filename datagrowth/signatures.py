from typing import Any
import hashlib
import json
import re
from pydantic import BaseModel, Field, PrivateAttr, field_validator, model_validator


SAFE_SIGNATURE_TYPE_PATTERN = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._-]*$")


class InputsValidator(BaseModel):
    args: tuple[Any, ...]
    kwargs: dict[str, Any]


class Signature(BaseModel):
    uri: str
    data: dict[str, Any] = Field(default_factory=dict)
    hash: int = Field(default=0)
    type: str | None = Field(default=None)
    args: tuple[Any, ...] = Field(default_factory=tuple)
    kwargs: dict[str, Any] = Field(default_factory=dict)
    _data_bytes: bytes | None = PrivateAttr(default=None)

    #####################
    # Data lifecycle
    #####################

    def set_data_bytes(self, data: bytes | None) -> None:
        self._data_bytes = data

    def get_data(self) -> dict[str, Any] | bytes:
        payload = self.data.get("payload")
        if not isinstance(payload, str) or not payload.startswith("bin://"):
            return self.data
        if self._data_bytes is None:
            raise RuntimeError("Signature.get_data() requires a signature to be open before reading bin:// data.")
        return self._data_bytes

    def close(self) -> None:
        self.set_data_bytes(None)

    #####################
    # Pydantic plumbing
    #####################

    model_config = {
        "frozen": True
    }

    def __hash__(self) -> int:
        return self.hash

    @field_validator("type")
    @classmethod
    def validate_type(cls, signature_type: str | None) -> str | None:
        if signature_type is None:
            return None
        if signature_type in {"", ".", ".."}:
            raise ValueError("Signature type must not be empty or a directory navigation token.")
        if "/" in signature_type or "\\" in signature_type:
            raise ValueError("Signature type must not contain path separators.")
        if not SAFE_SIGNATURE_TYPE_PATTERN.fullmatch(signature_type):
            raise ValueError(
                "Signature type contains unsupported characters. Allowed: letters, numbers, underscore, dash and dot."
            )
        return signature_type

    @staticmethod
    def _canonicalize_data(data: Any) -> Any:
        if isinstance(data, bytes):
            return {
                "__type__": "bytes",
                "sha256": hashlib.sha256(data).hexdigest(),
                "length": len(data),
            }
        if isinstance(data, dict):
            return {key: Signature._canonicalize_data(value) for key, value in data.items()}
        if isinstance(data, list):
            return [Signature._canonicalize_data(value) for value in data]
        if isinstance(data, tuple):
            return [Signature._canonicalize_data(value) for value in data]
        return data

    @staticmethod
    def _compute_hash(uri: str, data: Any) -> int:
        canonical_data = Signature._canonicalize_data(data)
        canonical = json.dumps({"uri": uri, "data": canonical_data}, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=False)
        return int(hashlib.sha256(canonical.encode("utf-8")).hexdigest(), 16)

    @model_validator(mode="before")
    @classmethod
    def set_hash(cls, values: Any) -> Any:
        if isinstance(values, dict):
            uri = values.get("uri")
            hash_ = values.get("hash")
            data = values.get("data") or {}
            if uri is None or hash_ is not None:
                return values
            # copy to avoid mutating caller's dict
            values = dict(values)
            values["hash"] = cls._compute_hash(uri, data) or hash_
        return values
