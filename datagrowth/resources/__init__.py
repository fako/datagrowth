# This file implements a lazy loading pattern to prevent Django from being imported too often.
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datagrowth.resources.http import (
        HttpFileResource,
        HttpImageResource,
        HttpResource,
        MicroServiceResource,
        TestClientResource,
        URLResource,
        file_resource_delete_handler,
    )
    from datagrowth.resources.shell import ShellResource


__all__ = [
    "ShellResource",
    "HttpResource",
    "HttpFileResource",
    "HttpImageResource",
    "file_resource_delete_handler",
    "URLResource",
    "MicroServiceResource",
    "TestClientResource",
]


def __getattr__(name: str) -> Any:
    if name == "ShellResource":
        from datagrowth.resources.shell import ShellResource as _ShellResource
        return _ShellResource

    if name in {
        "HttpResource",
        "HttpFileResource",
        "HttpImageResource",
        "file_resource_delete_handler",
        "URLResource",
        "MicroServiceResource",
        "TestClientResource",
    }:
        from datagrowth.resources.http import (
            HttpFileResource as _HttpFileResource,
            HttpImageResource as _HttpImageResource,
            HttpResource as _HttpResource,
            MicroServiceResource as _MicroServiceResource,
            TestClientResource as _TestClientResource,
            URLResource as _URLResource,
            file_resource_delete_handler as _file_resource_delete_handler,
        )
        return {
            "HttpResource": _HttpResource,
            "HttpFileResource": _HttpFileResource,
            "HttpImageResource": _HttpImageResource,
            "file_resource_delete_handler": _file_resource_delete_handler,
            "URLResource": _URLResource,
            "MicroServiceResource": _MicroServiceResource,
            "TestClientResource": _TestClientResource,
        }[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
