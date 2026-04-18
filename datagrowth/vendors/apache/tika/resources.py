from typing import Any, Literal, ClassVar, Type
import hashlib
import json
from pathlib import Path, PurePath
from pydantic import model_validator, HttpUrl, StrictBytes

from datagrowth.registry import Tag
from datagrowth.resources.protocols import ResourceStorageProtocol
from datagrowth.resources.http.pydantic import MicroServiceResource, MicroServiceInputsValidator
from datagrowth.signatures import InputsValidator, DataBody, DataMode
from datagrowth.resources.http.signature import HttpMethod, HttpSignature


class TikaInputsValidator(MicroServiceInputsValidator):

    document: StrictBytes | None = None
    file: PurePath | None = None
    url: HttpUrl | None = None

    @model_validator(mode="after")
    def validate_kwargs(self) -> "TikaInputsValidator":
        # Ensure that exactly one of document, file, or url is set, not more than one, and at least one.
        set_fields = [field for field in ("document", "file", "url") if getattr(self, field) is not None]
        if len(set_fields) != 1:
            raise ValueError(
                "Exactly one of 'document', 'file', or 'url' must be set (got: {}).".format(", ".join(set_fields))
            )
        return self


class HttpTikaResource(MicroServiceResource):

    NAMESPACE = Tag(category="namespace", value="tika_resource")
    INPUTS_VALIDATOR: ClassVar[Type[InputsValidator]] = TikaInputsValidator
    MICRO_SERVICE = "tika"
    MODE = DataMode.DATA
    METHOD = HttpMethod.PUT

    def headers(self, *args: Any, **kwargs: Any) -> dict[str, str]:
        headers = super().headers(*args, **kwargs)
        # Deside on using HTTP fetcher or not based on given input.
        if url := kwargs.get("url"):
            headers.update({
                "fetcherName": "http",
                "fetchKey": str(url),
            })
        return headers

    def data(self, **kwargs: Any) -> DataBody:
        if (document := kwargs.get("document")) is not None:
            if isinstance(document, bytes):
                if self.storage is None:
                    raise RuntimeError("Can't process bytes inside HttpTikaResource when there is no storage.")
                filename = f"{hashlib.sha256(document).hexdigest()}.bin"
                tmp_path = self.storage.write_tmp(filename, document)
                return DataBody(content=f"file://{tmp_path}")
            raise TypeError("Expected document to be bytes when document input is used.")
        if file_path := kwargs.get("file"):
            if file_path.is_absolute() and file_path.is_relative_to(Path.cwd()):
                file_path = file_path.relative_to(Path.cwd())
            return DataBody(content=f"file://{file_path}")
        if url := kwargs.get("url"):
            return DataBody(content=str(url))
        raise RuntimeError("Unreachable: Tika inputs require document, file, or url.")

    def prepare_inputs(self, *args: Any, **kwargs: Any) -> HttpSignature:
        signature = super().prepare_inputs(*args, **kwargs)
        updated_kwargs = dict(signature.kwargs)
        assert isinstance(signature.data, DataBody), "Tika DATA mode always produces a DataBody."
        loc = signature.data.content
        if loc.startswith("file://"):
            if updated_kwargs.get("document", None) is not None:
                updated_kwargs["document"] = loc
            if updated_kwargs.get("file", None) is not None:
                updated_kwargs["file"] = loc.removeprefix("file://")
        return signature.model_copy(update={"kwargs": updated_kwargs})

    def handle_errors(self) -> None:
        super().handle_errors()
        if self.result is None:
            return None
        has_content, exception_messages = self._inspect_tika_content()
        if has_content and exception_messages:
            self.status = 207
            exception_summary = ";\n".join(exception_messages)
            self.result = self.result.model_copy(update={
                "errors": f"Tika returned exceptions without extracted content:\n\n {exception_summary}",
            })
        elif not has_content and not exception_messages:
            self.status = 204
        elif not has_content and exception_messages:
            self.status = 1
            exception_summary = ";\n".join(exception_messages)
            self.result = self.result.model_copy(update={
                "errors": f"Tika returned exceptions without extracted content:\n\n {exception_summary}",
            })

    def close_snapshot(self, storage: ResourceStorageProtocol) -> None:
        assert self.signature is not None, "Expected signature to be set before closing snapshot."
        _, data = self.content
        if not data:
            return

        for ix, headers in enumerate(data):
            content = headers.pop("X-TIKA:content", None)
            if content is not None:
                content_filename = f"x-tika-content-{ix}.html"
                storage.write(self.signature, content_filename, content)
            headers_filename = f"tika-headers-{ix}.json"
            storage.write(self.signature, headers_filename, json.dumps(headers, indent=4))

    #####################
    # Helpers
    #####################

    def _inspect_tika_content(self) -> tuple[bool, list[str]]:
        _, data = self.content
        if not isinstance(data, list):
            return False, []

        has_content = False
        exception_messages: list[str] = []
        for result in data:
            if not isinstance(result, dict):
                continue
            has_content = has_content or bool(result.get("X-TIKA:content", None))
            result_exceptions = {key: value for key, value in result.items() if "X-TIKA:EXCEPTION:" in key}
            for key, value in result_exceptions.items():
                if isinstance(value, str) and value:
                    exception_messages.append(f"{key}: {value.splitlines()[0]}")
        return has_content, exception_messages


class PdfInputsValidator(TikaInputsValidator):
    POSITIONAL_NAMES = ("mode",)
    mode: Literal["semantic", "structure"] = "structure"


class PdfContentResource(HttpTikaResource):

    INPUTS_VALIDATOR: ClassVar[Type[InputsValidator]] = PdfInputsValidator
    PARAMETERS = {
        "mode": "{mode}"
    }

    def headers(self, *args: Any, **kwargs: Any) -> dict[str, str]:
        headers = super().headers(*args, **kwargs)
        # Set special PDF headers based on the inputs.
        headers["X-Tika-PDFextractMarkedContent"] = "true" if kwargs.get("mode") == "semantic" else "false"
        return headers
