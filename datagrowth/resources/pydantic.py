from __future__ import annotations

from typing import Any, ClassVar, Self, Generic, cast
from uuid import uuid4
from datetime import datetime, timedelta
from pydantic import BaseModel, Field, PrivateAttr, UUID4, field_serializer, model_validator

from datagrowth.configuration import ConfigurationType
from datagrowth.registry import DATAGROWTH_REGISTRY, Tag
from datagrowth.signatures import Signature, InputsValidator
from datagrowth.resources.protocols import ResourceExtractorProtocol, ResourceSignatureType, ResourceStorageProtocol


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

    NAMESPACE: ClassVar[Tag] = Tag(category="namespace", value="resource")
    STORAGE: ClassVar[Tag | None] = None
    EXTRACTOR: ClassVar[Tag | None] = None

    id: UUID4 = Field(default_factory=uuid4)
    type: Tag | None = Field(default=None)
    config: ConfigurationType | None = None
    signature: ResourceSignatureType | None = None
    result: Result | None = None

    status: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    purge_at: datetime | None = Field(default_factory=lambda: datetime.now() + timedelta(days=30))

    @property
    def storage(self) -> ResourceStorageProtocol["Resource[ResourceSignatureType]"] | None:
        return self._storage

    @property
    def extractor(self) -> ResourceExtractorProtocol[ResourceSignatureType, "Resource[ResourceSignatureType]"] | None:
        return self._extractor

    #####################
    # Publib interface
    #####################

    @classmethod
    def get_name(cls) -> str:
        return cls.__class__.__name__

    def extract(self, *args: Any, **kwargs: Any) -> Self:
        # Validate the inputs to arrive at a Signature used for extraction
        inputs = self.validate_inputs(*args, **kwargs)
        signature = self.prepare_inputs(*inputs.args, **inputs.kwargs)

        # Try to look up the Signature in storage
        if self.storage is not None:
            # Downgrade Signature to basic format and check against storage if extraction has taken place already
            if self.storage.config.allow_load:
                storage_signature = Signature(**signature.model_dump(mode="json"))
                loaded_resource = self.storage.load(storage_signature)
                if loaded_resource is not None:
                    return cast(Self, loaded_resource)

        # Validate that extraction is actually allowed/possible
        if self.extractor is None:
            raise NotImplementedError(
                f"{self.__class__.__name__} does not specify an extractor or implement the extract method."
            )

        # Attempt extracting data from the remote as prescribed by prepare_signature method
        self.signature = signature
        extracted = self.extractor.extract(signature)
        if isinstance(extracted, self.__class__):
            if not extracted.success:
                extracted.handle_errors()
            return cast(Self, extracted)
        self.signature = extracted.signature
        self.result = extracted.result
        self.status = extracted.status
        self.metadata = dict(extracted.metadata)
        if not self.success:
            self.handle_errors()
        return self

    def close(self) -> Self:
        if self.storage is not None and self.storage.config.allow_save:
            self.storage.save(self)
        return self

    @property
    def success(self) -> bool:
        raise NotImplementedError

    @property
    def content(self) -> tuple[str | None, Any]:
        if self.result is None:
            return None, None
        data = self.result.body if self.success else self.result.errors
        return self.result.content_type, data

    def validate_inputs(self, *args: Any, **kwargs: Any) -> InputsValidator:
        return InputsValidator(args=args, kwargs=kwargs)

    def prepare_inputs(self, *args: Any, **kwargs: Any) -> ResourceSignatureType:
        raise NotImplementedError

    def handle_errors(self) -> None:
        return None

    #####################
    # Pydantic plumbing
    #####################

    model_config = {
        "arbitrary_types_allowed": True
    }

    _storage: ResourceStorageProtocol["Resource[ResourceSignatureType]"] | None = PrivateAttr(default=None)
    _extractor: ResourceExtractorProtocol[ResourceSignatureType, "Resource[ResourceSignatureType]"] | None = PrivateAttr(default=None)  # noqa: E501

    def model_post_init(self, __context: Any) -> None:
        cls = self.__class__
        self._storage = DATAGROWTH_REGISTRY.get_storage(cls.STORAGE) if cls.STORAGE else None
        self._extractor = DATAGROWTH_REGISTRY.get_extractor(cls.EXTRACTOR) if cls.EXTRACTOR else None

    @classmethod
    def _get_config_namespaces(cls) -> list[str]:
        namespaces: list[str] = []
        for klass in cls.mro():
            namespace = klass.__dict__.get("NAMESPACE")
            if namespace is None:
                continue
            namespace_tags = [namespace] if isinstance(namespace, Tag) else list(namespace)
            for tag in namespace_tags:
                namespaces.append(tag.value)
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
