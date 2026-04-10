import requests

from datagrowth.processors import Processor


class ProcessorMock(Processor):

    def get_session(self):
        session = requests.Session()
        session.from_provider = True
        return session
