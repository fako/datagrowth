from typing import Any, ClassVar, Self
from pydantic import BaseModel, Field

from datagrowth.configuration import ConfigurationType
from datagrowth.resources.protocols import ResourceStorageProtocol
from datagrowth.signatures import InputsValidator, Signature


class MockResource(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    NAMESPACE: ClassVar[str] = "mock_resource"

    config: ConfigurationType = Field(default_factory=lambda: ConfigurationType(namespace=["global"]))

    def close(self) -> "MockResource":
        return self

    @classmethod
    def get_name(cls) -> str:
        return cls.__name__.lower()

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

    def validate_inputs(self, *args: Any, **kwargs: Any) -> InputsValidator:
        return InputsValidator(args=args, kwargs=kwargs)

    def prepare_inputs(self, *args: Any, **kwargs: Any) -> Signature:
        return Signature(uri="mock://")

    def close_snapshot(self, storage: ResourceStorageProtocol[Any]) -> None:
        return None
