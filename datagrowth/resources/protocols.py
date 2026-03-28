from typing import Protocol, Any, Self, TypeVar

from datagrowth.signatures import Signature


class ResourceProtocol(Protocol):
    """
    A set of methods and properties shared by Resources.
    This protocol gets used throughout Datagrowth to allow generic data ETL.
    """

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

    @property
    def success(self) -> bool:
        """
        This method indicates the success of the data gathering.
        """
        ...

    @property
    def content(self) -> tuple[str, Any]:
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


ResourceSignatureType = TypeVar("ResourceSignatureType", bound=Signature, contravariant=True)
ResourceType = TypeVar("ResourceType", bound=ResourceProtocol, covariant=True)


class ResourceStorageProtocol(Protocol[ResourceSignatureType, ResourceType]):

    def save(self, resource: ResourceType) -> None:
        ...

    def load(self, signature: ResourceSignatureType) -> ResourceType:
        ...


class ResourceExtractorProtocol(Protocol[ResourceSignatureType, ResourceType]):

    def extract(self, signature: ResourceSignatureType) -> ResourceType:
        ...
