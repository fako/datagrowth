from typing import Any
import base64
import hashlib
import json
from pydantic import BaseModel, Field, field_serializer, field_validator, model_validator


class InputsValidator(BaseModel):
    args: list[Any]
    kwargs: dict[str, Any]


class Signature(BaseModel):
    uri: str
    data: dict[str, Any] | bytes | None = Field(default=None)
    hash: int = Field(default=0)
    args: tuple[Any, ...] = Field(default_factory=tuple)
    kwargs: dict[str, Any] = Field(default_factory=dict)

    #####################
    # Pydantic plumbing
    #####################

    model_config = {
        "frozen": True
    }

    def __hash__(self) -> int:
        return self.hash

    @staticmethod
    def _encode_bytes_payload(value: Any) -> Any:
        if isinstance(value, bytes):
            return {
                "__type__": "bytes",
                "encoding": "base64",
                "value": base64.b64encode(value).decode("ascii"),
            }
        if isinstance(value, dict):
            return {key: Signature._encode_bytes_payload(item) for key, item in value.items()}
        if isinstance(value, list):
            return [Signature._encode_bytes_payload(item) for item in value]
        if isinstance(value, tuple):
            return [Signature._encode_bytes_payload(item) for item in value]
        return value

    @staticmethod
    def _decode_bytes_payload(value: Any) -> Any:
        if isinstance(value, dict):
            if value.get("__type__") == "bytes":
                encoded = value.get("value")
                if not isinstance(encoded, str):
                    raise TypeError("Serialized bytes payload should contain a base64 string value.")
                return base64.b64decode(encoded.encode("ascii"))
            return {key: Signature._decode_bytes_payload(item) for key, item in value.items()}
        if isinstance(value, list):
            return [Signature._decode_bytes_payload(item) for item in value]
        return value

    @field_serializer("data", when_used="json")
    def serialize_data(self, data: dict[str, Any] | bytes | None) -> Any:
        return self._encode_bytes_payload(data)

    @field_serializer("kwargs", when_used="json")
    def serialize_kwargs(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        return self._encode_bytes_payload(kwargs)

    @field_serializer("args", when_used="json")
    def serialize_args(self, args: tuple[Any, ...]) -> list[Any]:
        return self._encode_bytes_payload(args)

    @field_validator("data", mode="before")
    @classmethod
    def deserialize_data(cls, data: Any) -> Any:
        return cls._decode_bytes_payload(data)

    @field_validator("kwargs", mode="before")
    @classmethod
    def deserialize_kwargs(cls, kwargs: Any) -> Any:
        return cls._decode_bytes_payload(kwargs)

    @field_validator("args", mode="before")
    @classmethod
    def deserialize_args(cls, args: Any) -> Any:
        return cls._decode_bytes_payload(args)

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
    def _compute_hash(uri: str, data: dict[str, Any] | bytes) -> int:
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
