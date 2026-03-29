from unittest.mock import Mock, NonCallableMock

from datagrowth.resources import MicroServiceResource

from resources.mocks.requests import MockRequests


class MicroServiceResourceMock(MicroServiceResource):

    MICRO_SERVICE = "service_mock"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not isinstance(self.session, NonCallableMock):
            self.session = MockRequests
        if isinstance(self.session.send, Mock):
            self.session.send.reset_mock()
