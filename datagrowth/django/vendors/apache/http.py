from typing import Any
from pathlib import Path
import json

from django.conf import settings
from django.db import models
from datagrowth.configuration import DEFAULT_CONFIGURATION
from datagrowth.utils.data import override_dict

from datagrowth.resources.http import HttpResource


class HttpTikaResource(HttpResource):

    pdf_id = models.UUIDField(null=True, blank=True, db_index=True)

    CONFIG_DEFAULTS = override_dict(DEFAULT_CONFIGURATION, {  # can be managed by inheritance now
        "http_resource_force_data_file_to_payload": True
    })
    FILE_DATA_KEYS = ["document"]

    @property
    def URI_TEMPLATE(self) -> str:
        return f"{settings.TIKA_HOST}/rmeta/{settings.TIKA_RETURN_TYPE}"

    def variables(self, *args: Any) -> dict[str, Any]:
        args = args or (self.request.get("args") if self.request else tuple())
        return {
            "url": [],
            "mode": args[0] if len(args) else "structure"
        }

    def parameters(self, mode: Any, **kwargs: Any) -> dict[str, str]:
        parameters: dict[str, str] = super().parameters(**kwargs)
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

    def handle_errors(self) -> bool:
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
            return False
        return True

    def create_next_request(self) -> dict[str, Any] | None:
        main = self.get_main_content()
        if main is None:
            return None

        has_marked_content = main.get("pdf:hasMarkedContent", "false") == "true"
        if not has_marked_content or self.request["headers"].get("X-Tika-PDFextractMarkedContent") == "true":
            return None

        request: dict[str, Any] = self._create_request("put", "semantic", **self.request["kwargs"])
        return request

    #######################################################
    # TIKA METHODS
    #######################################################

    def get_main_content(self) -> dict[str, Any] | None:
        if not self.success:
            return None
        content_type, data = self.content
        main: dict[str, Any] = data[0]
        return main

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

    class Meta:
        abstract = True
