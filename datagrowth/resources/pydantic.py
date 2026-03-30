from __future__ import annotations

from typing import Any, ClassVar, Iterable, Self, Generic, cast
from uuid import uuid4
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, UUID4, field_serializer, model_validator

from datagrowth.configuration import ConfigurationType
from datagrowth.tags import Tag
from datagrowth.signatures import Signature
from datagrowth.resources.protocols import (ResourceExtractorProtocol, ResourceSignatureType, ResourceStorageProtocol,
                                            ResourceType)


def build_storage(kind: str) -> ResourceStorageProtocol[ResourceSignatureType, ResourceType] | None:
    # Placeholder resolver: concrete storage implementations can be registered later.
    if kind in {"", "none"}:
        return None
    raise NotImplementedError(f"Unsupported storage backend: {kind}")


def build_extractor(kind: str) -> ResourceExtractorProtocol[ResourceSignatureType, ResourceType] | None:
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


class Resource(BaseModel, Generic[ResourceSignatureType]):

    NAMESPACE: ClassVar[str | Iterable[str] | None] = "resource"
    STORAGE: ClassVar[str | None] = None
    EXTRACTOR: ClassVar[str | None] = None

    storage: ClassVar[ResourceStorageProtocol["Resource[ResourceSignatureType]"] | None] = None
    extractor: ClassVar[ResourceExtractorProtocol[ResourceSignatureType, "Resource[ResourceSignatureType]"] | None] = None  # noqa: E501

    id: UUID4 = Field(default_factory=uuid4)
    type: Tag | None = Field(default=None)
    config: ConfigurationType | None = None
    signature: ResourceSignatureType | None = None
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
        # Validate the inputs to arrive at a base Signature
        validated_signature = self.validate_inputs(*args, **kwargs)
        # Try to look up the Signature in storage
        if self.storage is not None:
            loaded_resource = self.storage.load(validated_signature)
            if loaded_resource is not None:
                return cast(Self, loaded_resource)
        # Attempt extracting data from the remote as prescribed by prepare_signature method
        if self.extractor is None:
            raise NotImplementedError(
                f"{self.__class__.__name__} does not specify an extractor or implement the extract method."
            )
        signature = self.prepare_signature(validated_signature)
        self.signature = signature
        return cast(Self, self.extractor.extract(signature))

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

    def validate_inputs(self, *args: Any, **kwargs: Any) -> Signature:
        raise NotImplementedError

    def prepare_signature(self, signature: Signature) -> ResourceSignatureType:
        raise NotImplementedError

    #####################
    # Pydantic plumbing
    #####################

    model_config = {
        "arbitrary_types_allowed": True
    }

    @classmethod
    def _get_config_namespaces(cls) -> list[str]:
        namespaces: list[str] = []
        for klass in cls.mro():
            namespace = klass.__dict__.get("NAMESPACE")
            if namespace is None:
                continue
            namespace_values = [namespace] if isinstance(namespace, str) else list(namespace)
            for value in namespace_values:
                if value and value not in namespaces:
                    namespaces.append(value)
        return namespaces or ["global"]

    @model_validator(mode="before")
    @classmethod
    def normalize_config(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        data = dict(data)
        raw_config = data.get("config")
        if raw_config is None:
            data["config"] = ConfigurationType(namespace=cls._get_config_namespaces())
        elif isinstance(raw_config, dict):
            config = ConfigurationType(namespace=cls._get_config_namespaces())
            config.update(raw_config)
            data["config"] = config
        elif not isinstance(raw_config, ConfigurationType):
            raise TypeError(
                f"Resource config expects a dict, ConfigurationType or None. Got {type(raw_config)}"
            )
        return data

    @field_serializer("config")
    def serialize_config(self, config: ConfigurationType | None, info: Any) -> dict[str, Any] | None:
        if config is None:
            return None
        context = info.context or {}
        protected = bool(context.get("config_protected", False))
        private = bool(context.get("config_private", False))
        return config.to_dict(protected=protected, private=private)

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
