from typing import Any
from enum import Enum
import hashlib
import json
import re
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator, model_validator


SAFE_SIGNATURE_TYPE_PATTERN = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9._-]*$")


class DataMode(str, Enum):
    NONE = "none"
    JSON = "json"
    DATA = "data"
    MULTIPART = "multipart"


class InputsValidator(BaseModel):
    args: tuple[Any, ...]
    kwargs: dict[str, Any]


class DataBody(BaseModel):
    """
    Used as data when Signature.mode is DATA.
    """
    content: str = Field(description="A locator to the content like file://... or content that gets encoded directly.")
    encoding: str | None = Field(default="utf-8")

    #####################
    # Pydantic plumbing
    #####################

    model_config = ConfigDict(extra="forbid", frozen=True)


class DataPart(BaseModel):
    """
    Used as data when Signature.mode is MULTIPART.
    """
    name: str
    content: str = Field(description="A locator to the content like file://..., content that gets encoded directly or string content.")  # noqa: E501
    encoding: str | None = Field(default="utf-8")
    content_type: str | None = Field(description="When set the Signature.get_data tries to encode the content.", default=None)  # noqa: E501
    filename: str | None = None

    #####################
    # Pydantic plumbing
    #####################

    model_config = ConfigDict(extra="forbid", frozen=True)


class Signature(BaseModel):
    uri: str
    data: dict[str, Any] | list[Any] | DataBody | list[DataPart] = Field(default_factory=dict)
    mode: DataMode = DataMode.NONE
    hash: int = Field(default=0)
    type: str | None = Field(default=None)
    args: tuple[Any, ...] = Field(default_factory=tuple)
    kwargs: dict[str, Any] = Field(default_factory=dict)
    _data_bytes: bytes | None = PrivateAttr(default=None)
    _data_parts: list[dict[str, Any]] | None = PrivateAttr(default=None)

    #####################
    # Data lifecycle
    #####################

    def set_data_bytes(self, data: bytes | None) -> None:
        self._data_bytes = data

    def set_data_parts(self, parts: list[dict[str, Any]] | None) -> None:
        self._data_parts = parts

    def get_data(self) -> dict[str, Any] | list[Any] | str | bytes | list[dict[str, Any]]:
        if self.mode == DataMode.JSON:
            return json.dumps(self.data, ensure_ascii=False, separators=(",", ":"))
        if self.mode == DataMode.DATA:
            if self._data_bytes is None:
                raise RuntimeError(
                    "Signature.get_data() requires the signature to be opened before reading DATA mode payloads."
                )
            return self._data_bytes
        if self.mode == DataMode.MULTIPART:
            if self._data_parts is None:
                raise RuntimeError(
                    "Signature.get_data() requires the signature to be opened before reading MULTIPART mode payloads."
                )
            return self._data_parts
        return self.data  # type: ignore[return-value]

    def close(self) -> None:
        self.set_data_bytes(None)
        self.set_data_parts(None)

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
    def _reject_bytes_in_value(obj: Any, path: str = "data") -> None:
        """Signature.data must be JSON-serializable; bytes belong in private attrs after open(), not in data."""
        if isinstance(obj, bytes):
            raise ValueError(
                f"{path} must not contain bytes; store a locator string (e.g. file://...) and resolve at open time."
            )
        if isinstance(obj, BaseModel):
            Signature._reject_bytes_in_value(obj.model_dump(mode="json"), path)
        elif isinstance(obj, dict):
            for key, value in obj.items():
                Signature._reject_bytes_in_value(value, f"{path}.{key}")
        elif isinstance(obj, (list, tuple)):
            for i, item in enumerate(obj):
                Signature._reject_bytes_in_value(item, f"{path}[{i}]")

    @model_validator(mode="before")
    @classmethod
    def coerce_data_and_set_hash(cls, values: Any) -> Any:
        """Coerce ``data`` to DataBody / list[DataPart] before hashing so canonical form is stable."""
        if not isinstance(values, dict):
            return values
        out = dict(values)
        mode = out.get("mode", DataMode.NONE)
        if isinstance(mode, DataMode):
            mode = mode.value
        data = out.get("data")
        if mode == "data":
            if isinstance(data, DataBody):
                pass
            elif isinstance(data, dict):
                out["data"] = DataBody.model_validate(data)
            elif data is None:
                out["data"] = DataBody.model_validate({})
            data = out.get("data")
        elif mode == "multipart" and isinstance(data, list):
            out["data"] = [p if isinstance(p, DataPart) else DataPart.model_validate(p) for p in data]
            data = out["data"]
        if data is None:
            data = {}
        uri = out.get("uri")
        hash_ = out.get("hash")
        if uri is not None and hash_ is None:
            out["hash"] = cls._compute_hash(uri, data, mode)
        return out

    @model_validator(mode="after")
    def validate_data_mode(self) -> "Signature":
        Signature._reject_bytes_in_value(self.data)
        if self.mode == DataMode.NONE:
            if not isinstance(self.data, dict):
                raise ValueError("DataMode.NONE requires data to be a dict.")
        elif self.mode == DataMode.JSON:
            if not isinstance(self.data, (dict, list)):
                raise ValueError("DataMode.JSON requires data to be a dict or list.")
        elif self.mode == DataMode.DATA:
            if not isinstance(self.data, DataBody):
                raise ValueError("DataMode.DATA requires data to be a DataBody.")
            enc = self.data.encoding
            if enc is not None and not isinstance(enc, str):
                raise ValueError("DataBody optional 'encoding' must be a string when set.")
        elif self.mode == DataMode.MULTIPART:
            if not isinstance(self.data, list):
                raise ValueError("DataMode.MULTIPART requires data to be a list of DataPart.")
            for part in self.data:
                if not isinstance(part, DataPart):
                    raise ValueError("Each MULTIPART entry must be a DataPart.")
                penc = part.encoding
                if penc is not None and not isinstance(penc, str):
                    raise ValueError("DataPart optional 'encoding' must be a string when set.")
        return self

    @staticmethod
    def _canonicalize_data(data: Any) -> Any:
        if isinstance(data, bytes):
            return {
                "__type__": "bytes",
                "sha256": hashlib.sha256(data).hexdigest(),
                "length": len(data),
            }
        if isinstance(data, BaseModel):
            return Signature._canonicalize_data(data.model_dump(mode="json"))
        if isinstance(data, dict):
            return {key: Signature._canonicalize_data(value) for key, value in data.items()}
        if isinstance(data, list):
            return [Signature._canonicalize_data(value) for value in data]
        if isinstance(data, tuple):
            return [Signature._canonicalize_data(value) for value in data]
        return data

    @staticmethod
    def _compute_hash(uri: str, data: Any, mode: str) -> int:
        canonical_data = Signature._canonicalize_data(data)
        canonical = json.dumps({"uri": uri, "data": canonical_data, "mode": mode}, sort_keys=True,
                               separators=(",", ":"), ensure_ascii=False)
        return int(hashlib.sha256(canonical.encode("utf-8")).hexdigest(), 16)
