from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from datagrowth.signatures import Signature


class HttpMethod(str, Enum):
    GET = "get"
    POST = "post"
    PUT = "put"
    HEAD = "head"
    PATCH = "patch"


class HttpAuth(BaseModel):
    headers: dict[str, str] = Field(default_factory=dict)
    parameters: dict[str, str] = Field(default_factory=dict)


class HttpSignature(Signature):
    method: HttpMethod
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    auth: HttpAuth | None = Field(default=None, exclude=True, repr=False)
