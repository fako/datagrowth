from typing import ClassVar

from datagrowth.registry import Tag
from datagrowth.vendors.apache.tika.resources import (
    HttpTikaResource as HttpTikaResourceNoStorage, TikaInputsValidator,
    PdfContentResource as PdfContentResourceNoStorage, PdfInputsValidator
)

__all__ = [
    "HttpTikaResource",
    "PdfContentResource",
    "TikaInputsValidator",
    "PdfInputsValidator",
]


class HttpTikaResource(HttpTikaResourceNoStorage):
    STORAGE: ClassVar[Tag | None] = Tag(category="storage", value="file_system")


class PdfContentResource(PdfContentResourceNoStorage):
    STORAGE: ClassVar[Tag | None] = Tag(category="storage", value="file_system")
