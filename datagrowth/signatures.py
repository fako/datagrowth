from typing import Any
import hashlib
import json
from pydantic import BaseModel, Field, model_validator


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
