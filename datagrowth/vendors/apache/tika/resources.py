from typing import Any, Literal
import hashlib
import json
from pathlib import Path, PurePath
from pydantic import Field, model_validator, HttpUrl, StrictBytes

from datagrowth.registry import Tag
from datagrowth.resources.protocols import ResourceStorageProtocol
from datagrowth.resources.http.pydantic import MicroServiceResource, HttpResourceInputsValidator
from datagrowth.resources.http.signature import HttpMode


class TikaInputsValidator(HttpResourceInputsValidator):
    args: tuple[Any, ...] = Field(min_length=1, max_length=2)
    kwargs: dict[str, Any] = Field(default_factory=dict, min_length=0, max_length=0)
    mode: Literal["semantic", "structure"] = "structure"
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
        # Dump inputs into the kwargs for further processing by HttpSignature
        self.kwargs = self.model_dump(exclude={"args", "kwargs"})
        return self


class HttpTikaResource(MicroServiceResource):

    NAMESPACE = Tag(category="namespace", value="tika_resource")
    MICRO_SERVICE = "tika"
    MODE = HttpMode.DATA
    PARAMETERS = {
        "mode": "{mode}"
    }

    def validate_inputs(self, *args: Any, **kwargs: Any) -> TikaInputsValidator:
        """
        Takes the extraction mode from the (optional) first argument and validates Tika can handle the other inputs.
        Sets the method to PUT, because Tika doesn't except other methods.
        """
        if len(args):
            kwargs["mode"] = args[0]
        kwargs["args"] = ("put",) + args
        kwargs["kwargs"] = {}
        return TikaInputsValidator(**kwargs)

    def headers(self, *args: Any, **kwargs: Any) -> dict[str, str]:
        headers = super().headers(*args, **kwargs)
        # Set special Tika headers based on the inputs.
        headers["X-Tika-PDFextractMarkedContent"] = "true" if kwargs.get("mode") == "semantic" else "false"
        # Deside on using HTTP fetcher or not based on given input.
        if url := kwargs.get("url"):
            headers.update({
                "fetcherName": "http",
                "fetchKey": str(url),
            })
        return headers

    def data(self, **kwargs: Any) -> dict[str, str]:
        if document := kwargs.get("document"):
            if isinstance(document, bytes):
                if self.storage is None:
                    raise RuntimeError("Can't process bytes inside HttpTikaResource when there is no storage.")
                filename = f"{hashlib.sha256(document).hexdigest()}.bin"
                tmp_path = self.storage.write_tmp(filename, document)
                return {"payload": f"bin://file://{tmp_path}"}
            raise TypeError("Expected document to be bytes when document input is used.")
        if file_path := kwargs.get("file"):
            if file_path.is_absolute() and file_path.is_relative_to(Path.cwd()):
                file_path = file_path.relative_to(Path.cwd())
            return {"payload": f"bin://file://{file_path}"}
        if url := kwargs.get("url"):
            # Keep URL-mode signatures distinct by adding URL to the data. Tika will ignore this input.
            return {"payload": str(url)}
        return {}

    def prepare_inputs(self, *args: Any, **kwargs: Any):
        signature = super().prepare_inputs(*args, **kwargs)
        kwargs = dict(signature.kwargs)
        data = signature.data
        payload = data.get("payload") if isinstance(data, dict) else data
        if isinstance(payload, str) and payload.startswith("bin://file://"):
            if kwargs.get("document", None) is not None:
                kwargs["document"] = payload
            if kwargs.get("file", None) is not None:
                kwargs["file"] = payload.removeprefix("bin://file://")
        return signature.model_copy(update={
            "data": payload,
            "kwargs": kwargs,
        })

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
