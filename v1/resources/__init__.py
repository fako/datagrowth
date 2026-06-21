from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from .base import Resource, Result
    from .http.base import (
        HttpInputsValidator,
        HttpResource,
        MicroServiceInputsValidator,
        MicroServiceResource,
        URLInputsValidator,
        URLResource,
    )
    from .http.extractors.requests import RequestsExtractor
    from .http.signature import HttpAuth, HttpMethod, HttpSignature
    from .prompt.base import PromptErrorCodes, PromptInputsValidator, PromptResource
    from .session.base import SessionResource
    from .storage.file_system import FileSystemStorage


__all__ = [
    "Result",
    "Resource",
    "HttpMethod",
    "HttpAuth",
    "HttpSignature",
    "HttpInputsValidator",
    "HttpResource",
    "URLInputsValidator",
    "URLResource",
    "MicroServiceInputsValidator",
    "MicroServiceResource",
    "RequestsExtractor",
    "PromptErrorCodes",
    "PromptInputsValidator",
    "PromptResource",
    "FileSystemStorage",
    "SessionResource",
]


def __getattr__(name: str) -> Any:
    if name in {"Resource", "Result"}:
        from .base import Resource, Result
        return {"Resource": Resource, "Result": Result}[name]

    if name in {
        "HttpInputsValidator",
        "HttpResource",
        "MicroServiceInputsValidator",
        "MicroServiceResource",
        "URLInputsValidator",
        "URLResource",
    }:
        from .http.base import (
            HttpInputsValidator,
            HttpResource,
            MicroServiceInputsValidator,
            MicroServiceResource,
            URLInputsValidator,
            URLResource,
        )
        return {
            "HttpInputsValidator": HttpInputsValidator,
            "HttpResource": HttpResource,
            "MicroServiceInputsValidator": MicroServiceInputsValidator,
            "MicroServiceResource": MicroServiceResource,
            "URLInputsValidator": URLInputsValidator,
            "URLResource": URLResource,
        }[name]

    if name == "RequestsExtractor":
        from .http.extractors.requests import RequestsExtractor
        return RequestsExtractor

    if name in {"HttpAuth", "HttpMethod", "HttpSignature"}:
        from .http.signature import HttpAuth, HttpMethod, HttpSignature
        return {"HttpAuth": HttpAuth, "HttpMethod": HttpMethod, "HttpSignature": HttpSignature}[name]

    if name in {"PromptErrorCodes", "PromptInputsValidator", "PromptResource"}:
        from .prompt.base import PromptErrorCodes, PromptInputsValidator, PromptResource
        return {
            "PromptErrorCodes": PromptErrorCodes,
            "PromptInputsValidator": PromptInputsValidator,
            "PromptResource": PromptResource,
        }[name]

    if name == "FileSystemStorage":
        from .storage.file_system import FileSystemStorage
        return FileSystemStorage

    if name == "SessionResource":
        from .session.base import SessionResource
        return SessionResource

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
