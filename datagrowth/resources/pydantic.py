from __future__ import annotations

from typing import Any, ClassVar, Self
from uuid import uuid4
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, UUID4

from datagrowth.tags import Tag
from datagrowth.signatures import Signature
from datagrowth.resources.protocols import ResourceExtractorProtocol, ResourceStorageProtocol


def build_storage(kind: str) -> ResourceStorageProtocol | None:
    # Placeholder resolver: concrete storage implementations can be registered later.
    if kind in {"", "none"}:
        return None
    raise NotImplementedError(f"Unsupported storage backend: {kind}")


def build_extractor(kind: str) -> ResourceExtractorProtocol | None:
    # Placeholder resolver: concrete extractor implementations can be registered later.
    if kind in {"", "none"}:
        return None
    raise NotImplementedError(f"Unsupported extractor backend: {kind}")


class Result(BaseModel):
    content_type: str
    head: dict[str, str] = Field(default_factory=dict)
    body: str | None = None
    errors: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)

    model_config = {
        "frozen": True
    }


class Resource(BaseModel):

    STORAGE: ClassVar[str | None] = None
    EXTRACTOR: ClassVar[str | None] = None

    storage: ClassVar[ResourceStorageProtocol | None] = None
    extractor: ClassVar[ResourceExtractorProtocol | None] = None

    id: UUID4 = Field(default_factory=uuid4)
    type: Tag | None = Field(default=None)
    signature: Signature | None = None
    result: Result | None = None

    status: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    purge_at: datetime | None = Field(default_factory=lambda: datetime.now() + timedelta(days=30))

    #####################
    # Publib interface
    #####################

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls.storage = build_storage(cls.STORAGE or "none")
        cls.extractor = build_extractor(cls.EXTRACTOR or "none")

    def extract(self, *args: Any, **kwargs: Any) -> Self:
        if self.extractor is None:
            raise NotImplementedError(
                f"{self.__class__.__name__} does not specify an extractor or implement the extract method."
            )
        return self.extractor.extract(self.signature)

    def close(self) -> Self:
        if self.storage is not None:
            self.storage.save(self)
        return self

    @property
    def success(self) -> bool:
        return True

    @property
    def content(self) -> tuple[str | None, Any]:
        if self.result is None:
            return None, None
        data = self.result.body if self.success else self.result.errors
        return self.result.content_type, data

    #####################
    # Pydantic plumbing
    #####################

    def _equality_key(self) -> tuple:
        # Include type if it matters for identity
        if self.signature is not None:
            return "sig", self.type, self.signature.hash
        return "id", self.type, self.id

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Resource):
            return NotImplemented
        return self._equality_key() == other._equality_key()

    def __hash__(self) -> int:
        return hash(self._equality_key())
