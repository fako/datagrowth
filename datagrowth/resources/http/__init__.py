from datagrowth.resources.http.extractors.requests import RequestsExtractor
from datagrowth.resources.storage.file_system import FileSystemStorage

# Below this file implements a lazy loading pattern to prevent Django from being imported too often.
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datagrowth.resources.http.decorators import load_session
    from datagrowth.resources.http.files import HttpFileResource, HttpImageResource, file_resource_delete_handler
    from datagrowth.resources.http.generic import HttpResource, MicroServiceResource, TestClientResource, URLResource
    from datagrowth.resources.http.iterators import send_iterator, send_serie_iterator


__all__ = [
    "HttpResource",
    "URLResource",
    "MicroServiceResource",
    "TestClientResource",
    "HttpFileResource",
    "HttpImageResource",
    "file_resource_delete_handler",
    "load_session",
    "send_iterator",
    "send_serie_iterator",
]


def __getattr__(name: str) -> Any:
    if name in {"HttpResource", "URLResource", "MicroServiceResource", "TestClientResource"}:
        from datagrowth.resources.http.generic import (
            HttpResource as _HttpResource,
            MicroServiceResource as _MicroServiceResource,
            TestClientResource as _TestClientResource,
            URLResource as _URLResource,
        )
        return {
            "HttpResource": _HttpResource,
            "URLResource": _URLResource,
            "MicroServiceResource": _MicroServiceResource,
            "TestClientResource": _TestClientResource,
        }[name]

    if name in {"HttpFileResource", "HttpImageResource", "file_resource_delete_handler"}:
        from datagrowth.resources.http.files import (
            HttpFileResource as _HttpFileResource,
            HttpImageResource as _HttpImageResource,
            file_resource_delete_handler as _file_resource_delete_handler,
        )
        return {
            "HttpFileResource": _HttpFileResource,
            "HttpImageResource": _HttpImageResource,
            "file_resource_delete_handler": _file_resource_delete_handler,
        }[name]

    if name == "load_session":
        from datagrowth.resources.http.decorators import load_session as _load_session
        return _load_session

    if name in {"send_iterator", "send_serie_iterator"}:
        from datagrowth.resources.http.iterators import (
            send_iterator as _send_iterator,
            send_serie_iterator as _send_serie_iterator,
        )
        return {
            "send_iterator": _send_iterator,
            "send_serie_iterator": _send_serie_iterator,
        }[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
