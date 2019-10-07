from unittest.mock import Mock, NonCallableMock

from django.db.models import QuerySet

from datagrowth.resources.http import HttpResource

from resources.mocks.requests import MockRequests


MockErrorQuerySet = Mock(QuerySet)
MockErrorQuerySet.count = Mock(return_value=0)


class HttpResourceMock(HttpResource):

    URI_TEMPLATE = "http://localhost:8000/{}/?q={}"
    PARAMETERS = {
        "param": 1
    }
    HEADERS = {
        "Accept": "application/json"
    }
    FILE_DATA_KEYS = ["file"]
    GET_SCHEMA = {
        "args": {
            "title": "resource mock arguments",
            "type": "array",  # a single alphanumeric element
            "items": [
                {
                    "type": "string",
                    "enum": ["en", "nl"]
                },
                {
                    "type": "string",
                    "pattern": "[A-Za-z0-9]+"
                }
            ],
            "additionalItems": False,
            "minItems": 2
        },
        "kwargs": None  # not allowed
    }
    POST_SCHEMA = {
        "args": {
            "title": "resource mock arguments",
            "type": "array",  # a single alphanumeric element
            "items": [
                {
                    "type": "string",
                    "enum": ["en", "nl"]
                },
                {
                    "type": "string",
                    "pattern": "[A-Za-z0-9]+"
                }
            ],
            "additionalItems": False,
            "minItems": 2
        },
        "kwargs": {
            "title": "resource mock keyword arguments",
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "file": {"type": "string"}
            },
            "required": ["query"]
        }
    }

    CONFIG_NAMESPACE = "mock"

    def __init__(self, *args, **kwargs):
        super(HttpResourceMock, self).__init__(*args, **kwargs)
        if not isinstance(self.session, NonCallableMock):
            self.session = MockRequests
        if isinstance(self.session.send, Mock):
            self.session.send.reset_mock()

    def send(self, method, *args, **kwargs):
        if method == "post":
            query = kwargs.get("query")
            if query:
                args += (query,)
            args = (self.config.source_language,) + args
        elif method == "get":
            args = (self.config.source_language,) + args
        return super(HttpResourceMock, self).send(method, *args, **kwargs)

    def auth_parameters(self):
        return {
            "auth": 1,
            "key": self.config.secret
        }

    def next_parameters(self):
        content_type, data = self.content
        try:
            nxt = data["next"]
        except (KeyError, TypeError):
            return {}
        return {"next": nxt}

    def data(self, **kwargs):
        kwargs["test"] = kwargs.pop("query", None)
        return kwargs

    def parameters(self, **kwargs):
        params = super().parameters()
        params.update(**kwargs)
        params.pop("url", None)
        return params

    def variables(self, *args):
        args = args or (self.request["args"] if self.request else tuple())
        return {
            "url": args,
            "meta": args[1] if len(args) > 1 else None
        }
