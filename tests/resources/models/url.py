from unittest.mock import Mock, NonCallableMock

from datagrowth.resources import URLResource

from resources.mocks.requests import MockRequests


class URLResourceMock(URLResource):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not isinstance(self.session, NonCallableMock):
            self.session = MockRequests
        if isinstance(self.session.send, Mock):
            self.session.send.reset_mock()

    def data(self, **kwargs):
        kwargs["test"] = kwargs.pop("query", None)
        return kwargs
