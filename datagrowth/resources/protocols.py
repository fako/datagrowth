from typing import Protocol, Any, Self, TypeVar, ClassVar, Type
from pathlib import Path

from datagrowth.signatures import Signature, InputsValidator
from datagrowth.configuration import ConfigurationProperty, ConfigurationType


ResourceSignatureType = TypeVar("ResourceSignatureType", bound=Signature)


class ResourceProtocol(Protocol):
    """
    A set of methods and properties shared by Resources.
    This protocol gets used throughout Datagrowth to allow generic data ETL.
    """
    INPUTS_VALIDATOR: ClassVar[Type[InputsValidator]]

    config: ConfigurationType

    @property
    def signature(self) -> Signature | None:
        """Read-only Signature property to stay covariant — Signature subclasses (e.g. HttpSignature) must match."""
        ...

    def close(self) -> Self:
        """
        Stores extracted data to disk if any was retrieved and possibly stores empty Resource object.
        """
        ...

    @classmethod
    def get_name(cls) -> str:
        """
        Returns a human readable name of the Resource class.
        """
        ...

    #######################################################
    # TEMPLATE METHODS
    #######################################################
    # A set of methods and properties shared by resources
    # and meant to override to adjust functionality.

    def prepare_extract(self, *args: Any, **kwargs: Any) -> Signature:
        """
        Takes arbitrary input data and performs the validation and transformation necessary to execute data extraction.
        """
        ...

    def extract(self, *args: Any, **kwargs: Any) -> Self:
        """
        Implements a strategy for extracting data from the source that the Resource represents.
        """
        ...

    def next(self) -> Self | None:
        """
        Creates a new Resource that is the follow-up of the current Resource,
        like the Resource for a next page in a Resource that supports pagination.
        Or returns None if no such follow-up exists.
        """
        ...

    @property
    def success(self) -> bool:
        """
        This method indicates the success of the data gathering.
        """
        ...

    @property
    def content(self) -> tuple[str | None, Any]:
        """
        This method returns the content_type and data from the resource.
        """
        ...

    def handle_errors(self) -> None:
        """
        Override this method to handle resource specific error cases.
        Usually you'd raise a particular ``DGResourceException`` to indicate particular errors.
        """
        ...

    def prepare_inputs(self, inputs: InputsValidator) -> Signature:
        """
        Override this method to turn validated inputs into a ResourceType specific signature to use for extraction.
        """
        ...

    def close_snapshot(self, storage: "ResourceStorageProtocol") -> None:
        """
        Override this method to customize data storage when Resource is used in snapshot mode during tests.
        """
        ...


ExtractorSignatureType = TypeVar("ExtractorSignatureType", bound=Signature, contravariant=True)


class ResourceStorageProtocol(Protocol):

    config: ConfigurationProperty | ConfigurationType

    def save(self, resource: ResourceProtocol) -> Signature:
        ...

    def load(self, signature: Signature) -> ResourceProtocol | None:
        ...

    def read(self, signature: Signature, filename: str) -> bytes | str:
        ...

    def write(self, signature: Signature, filename: str, data: bytes | str) -> Path:
        ...

    def read_tmp(self, filename: str) -> bytes | str:
        ...

    def write_tmp(self, filename: str, data: bytes | str) -> Path:
        ...


class ResourceExtractorProtocol(Protocol[ExtractorSignatureType]):

    config: ConfigurationProperty | ConfigurationType

    def extract(self, signature: ExtractorSignatureType) -> ResourceProtocol:
        ...
