from typing import Any, Literal
from pathlib import Path, PurePath
from pydantic import Field, model_validator, HttpUrl, StrictBytes

from datagrowth.registry import Tag
from datagrowth.signatures import InputsValidator
from datagrowth.resources.http.pydantic import MicroServiceResource
from datagrowth.resources.http.signature import HttpMode


class TikaInputsValidator(InputsValidator):
    args: list[Any] = Field(min_length=1, max_length=2)
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
            raise ValueError("Exactly one of 'document', 'file', or 'url' must be set (got: {}).".format(", ".join(set_fields)))  # noqa: E501
        # Dump inputs into the kwargs for further processing by HttpSignature
        self.kwargs = self.model_dump(exclude={"args", "kwargs"})
        return self


class HttpTikaResource(MicroServiceResource):

    NAMESPACE = Tag(category="namespace", value="tika_resource")
    MICRO_SERVICE = "tika"
    MODE = HttpMode.BYTES
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

    def data(self, **kwargs: Any) -> bytes | None:
        if document := kwargs.get("document"):
            if isinstance(document, bytes):
                return document
            raise TypeError("Expected document to be bytes when document input is used.")
        if file_path := kwargs.get("file"):
            return Path(file_path).read_bytes()
        if url := kwargs.get("url"):
            # Keep URL-mode signatures distinct by adding URL to the data. Tika will ignore this input.
            return str(url).encode("utf-8")
        return None

    def handle_errors(self) -> None:
        super().handle_errors()
        _, data = self.content
        has_content = False
        has_exception = False

        for rsl in data:
            has_content = has_content or bool(rsl.get("X-TIKA:content", None))
            rsl_exceptions = dict(filter(lambda key: "X-TIKA:EXCEPTION:" in key, rsl.keys()))
            has_exception = has_exception or len(rsl_exceptions) > 0

        if has_content and has_exception:
            self.status = 200
        elif not has_content and not has_exception:
            self.status = 204
        elif not has_content and has_exception:
            self.status = 1
