from typing import Any, ClassVar, Type, Self
from pydantic import BaseModel, Field

from datagrowth.configuration import ConfigurationType
from datagrowth.resources.protocols import ResourceStorageProtocol
from datagrowth.signatures import InputsValidator, Signature


class MockResource(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    NAMESPACE: ClassVar[str] = "mock_resource"
    INPUTS_VALIDATOR: ClassVar[Type[InputsValidator]] = InputsValidator

    config: ConfigurationType = Field(default_factory=lambda: ConfigurationType(namespace=["global"]))
    signature: Signature | None = None

    def close(self) -> "MockResource":
        return self

    @classmethod
    def get_name(cls) -> str:
        return cls.__name__.lower()

    def prepare_extract(self, *args: Any, **kwargs: Any) -> Signature:
        return Signature(uri="mock://")

    def extract(self, *args: Any, **kwargs: Any) -> "MockResource":
        return self

    @property
    def success(self) -> bool:
        return True

    @property
    def content(self) -> tuple[str, dict[str, Any]]:
        return "application/json", {}

    def handle_errors(self) -> None:
        return None

    def next(self) -> Self | None:
        return None

    def prepare_inputs(self, inputs: InputsValidator) -> Signature:
        return Signature(uri="mock://")

    def close_snapshot(self, storage: ResourceStorageProtocol) -> None:
        return None
