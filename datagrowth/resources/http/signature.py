from __future__ import annotations

from typing import Any, ClassVar
from enum import Enum
import json

from pydantic import BaseModel, Field

from datagrowth.signatures import DataMode, Signature


class HttpMethod(str, Enum):
    GET = "get"
    POST = "post"
    PUT = "put"
    HEAD = "head"
    PATCH = "patch"


class HttpAuth(BaseModel):
    headers: dict[str, str] = Field(default_factory=dict)
    parameters: dict[str, str] = Field(default_factory=dict)
    data: dict[str, Any] = Field(default_factory=dict)


class HttpSignature(Signature):
    method: HttpMethod
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    auth: HttpAuth | None = Field(default=None, exclude=True, repr=False)

    HASH_FIELDS: ClassVar[list[str]] = ["uri", "data", "mode", "method"]

    def get_data(self) -> dict[str, Any] | list[Any] | str | bytes | list[dict[str, Any]]:
        data = super().get_data()
        auth_data = self.auth.data if self.auth is not None else {}
        if not auth_data:
            return data

        if self.mode == DataMode.JSON:
            if not isinstance(data, str):
                raise TypeError(f"JSON mode expected serialized string data, got {type(data).__name__}.")
            decoded = json.loads(data)
            if not isinstance(decoded, dict):
                raise TypeError("HttpAuth.data can only be merged into a JSON object body.")
            decoded.update(auth_data)
            return json.dumps(decoded, ensure_ascii=False, separators=(",", ":"))

        if not isinstance(data, dict):
            raise TypeError(
                f"HttpAuth.data can only be merged into a dictionary body, got {type(data).__name__} "
                f"for {self.mode.value} mode."
            )
        merged = dict(data)
        merged.update(auth_data)
        return merged
