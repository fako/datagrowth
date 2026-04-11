from typing import Protocol, Any, Self, TypeVar
from pathlib import Path

from datagrowth.signatures import Signature, InputsValidator
from datagrowth.configuration import ConfigurationType


ResourceSignatureType = TypeVar("ResourceSignatureType", bound=Signature)


class ResourceProtocol(Protocol):
    """
    A set of methods and properties shared by Resources.
    This protocol gets used throughout Datagrowth to allow generic data ETL.
    """

    config: ConfigurationType

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

    def validate_inputs(self, *args: Any, **kwargs: Any) -> InputsValidator:
        """
        Override this method to run a (Pydantic) validator against the inputs before they get processed.
        """
        ...

    def prepare_inputs(self, *args: Any, **kwargs: Any) -> Signature:
        """
        Override this method to turn inputs into a ResourceType specific signature to use for extraction.
        """
        ...

    def close_snapshot(self, storage: "ResourceStorageProtocol") -> None:
        """
        Override this method to customize data storage when Resource is used in snapshot mode during tests.
        """
        ...


ResourceType = TypeVar("ResourceType", bound=ResourceProtocol)
ExtractorSignatureType = TypeVar("ExtractorSignatureType", bound=Signature, contravariant=True)
ExtractorResourceType = TypeVar("ExtractorResourceType", bound=ResourceProtocol, covariant=True)


class ResourceStorageProtocol(Protocol[ResourceType]):

    config: ConfigurationType

    def save(self, resource: ResourceType) -> Signature:
        ...

    def load(self, signature: Signature) -> ResourceType | None:
        ...

    def read(self, signature: Signature, filename: str) -> bytes | str:
        ...

    def write(self, signature: Signature, filename: str, data: bytes | str) -> Path:
        ...

    def read_tmp(self, filename: str) -> bytes | str:
        ...

    def write_tmp(self, filename: str, data: bytes | str) -> Path:
        ...


class ResourceExtractorProtocol(Protocol[ExtractorSignatureType, ExtractorResourceType]):

    config: ConfigurationType

    def extract(self, signature: ExtractorSignatureType) -> ExtractorResourceType:
        ...
