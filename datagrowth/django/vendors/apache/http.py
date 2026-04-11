from typing import Any, cast
from pathlib import Path
import json

from django.db import models


from datagrowth.resources.http import MicroServiceResource


class HttpTikaResource(MicroServiceResource):

    pdf_id = models.UUIDField(null=True, blank=True, db_index=True)

    MICRO_SERVICE = "tika"
    CONFIG_NAMESPACE = "tika_resource"
    FILE_DATA_KEYS = ["document"]

    def variables(self, *args: Any) -> dict[str, Any]:
        request_args = self.request.get("args", tuple()) if self.request else tuple()
        resolved_args: tuple[Any, ...] = tuple(args) if args else tuple(request_args or tuple())
        has_connection_args = len(resolved_args) >= 3
        return {
            "url": list(resolved_args[:3]) if has_connection_args else [],
            "mode": resolved_args[3] if len(resolved_args) > 3 else (resolved_args[0] if resolved_args else "structure"),
        }

    def parameters(self, mode: Any = None, **kwargs: Any) -> dict[str, str]:
        base_parameters = cast(dict[str, str] | None, super().parameters(**kwargs))
        parameters: dict[str, str] = base_parameters or {}
        if mode == "semantic":
            parameters["mode"] = mode
        return parameters

    def headers(self, *args: Any, **kwargs: Any) -> Any:
        headers = super().headers(*args, **kwargs)
        variables = self.variables(*args)
        # Set Tika options based on the inputs.
        headers["X-Tika-PDFextractMarkedContent"] = "true" if variables.get("mode") == "semantic" else "false"
        # Deside on using HTTP fetcher or not based on given document input.
        document = kwargs.get("document")
        if document is None or not document.startswith("http"):
            return headers
        # Encountered a document with the http protocol. Use the HTTP fetcher.
        headers.update({
            "fetcherName": "http",
            "fetchKey": document,
        })
        return headers

    def data(self, **kwargs: Any) -> Any:
        document = kwargs.pop("document", None)
        if document is None or not document.startswith("file"):
            return super().data(**kwargs)
        # Encountered a document with the file protocol. Let HttpResource handle casting to bytes.
        return {"document": document.replace("file://", "")}

    def handle_errors(self) -> None:
        super().handle_errors()
        _, data = self.content
        if not data:
            return None
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
        return None

    def create_next_request(self) -> dict[str, Any] | None:
        main = self.get_main_content()
        if main is None:
            return None

        has_marked_content = main.get("pdf:hasMarkedContent", "false") == "true"
        if not has_marked_content or self.request["headers"].get("X-Tika-PDFextractMarkedContent") == "true":
            return None

        request_args = self.request.get("args", tuple()) if self.request else tuple()
        if len(request_args) >= 3:
            connection_args = tuple(request_args[:3])
        else:
            connection_args = (
                self.connection["protocol"],
                self.connection["host"],
                self.connection["path"],
            )
        request: dict[str, Any] = self._create_request("put", *connection_args, "semantic", **self.request["kwargs"])
        return request

    #######################################################
    # TIKA METHODS
    #######################################################

    def get_main_content(self) -> dict[str, Any] | None:
        if not self.success:
            return None
        _, data = self.content
        if not isinstance(data, list) or not data:
            return None
        main = data[0]
        if not isinstance(main, dict):
            return None
        return cast(dict[str, Any], main)

    def inject_alternative_content(self, key: str, content: str) -> None:
        main = self.get_main_content()
        if main is None:
            return None
        main[key] = content
        self.body = json.dumps([main])
        self.close()
        return None

    def set_pdf_id(self) -> None:
        main = self.get_main_content()
        if main is None:
            return None
        pdf_id = main.get("xmpMM:DocumentID")
        if pdf_id:
            pdf_id = pdf_id.replace("uuid:", "").lower()
        self.pdf_id = pdf_id
        return None

    @property
    def file_path(self) -> Path | None:
        if not self.request:
            return None
        if self.request["kwargs"]["document"].startswith("file"):
            return Path(self.request["kwargs"]["document"].replace("file://", ""))
        return None

    def __str__(self) -> str:
        if self.request:
            return f"{self.__class__.__name__}(document={self.request["kwargs"]["document"]})"
        return f"{self.__class__.__name__}(document=None)"

    class Meta(MicroServiceResource.Meta):
        abstract = True
