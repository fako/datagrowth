from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from datagrowth.signatures import Signature


class HttpMode(str, Enum):
    """
    Explicit request payload modes for transport implementations.
    We keep this explicit (instead of auto-inference) so behavior is predictable
    across clients like requests, async clients and Django test client.
    """
    NONE = "none"
    JSON = "json"
    DATA = "data"
    BYTES = "bytes"
    MULTIPART = "multipart"


class HttpMethod(str, Enum):
    """
    Supported HTTP verbs for HttpSignature requests.
    Keep this explicit so unsupported methods fail during signature validation.
    """
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
    mode: HttpMode = HttpMode.NONE
