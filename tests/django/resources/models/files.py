from unittest.mock import Mock, NonCallableMock

from datagrowth.resources import HttpImageResource

from resources.mocks.requests import MockFileRequests


class HttpImageResourceMock(HttpImageResource):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not isinstance(self.session, NonCallableMock):
            self.session = MockFileRequests
        if isinstance(self.session.send, Mock):
            self.session.send.reset_mock()

    def get_file_name(self, original, now):
        return original
